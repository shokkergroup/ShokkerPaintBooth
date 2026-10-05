# -*- coding: utf-8 -*-
"""WR-P5 corrections for the independently rejected Petri W4 board.

W4 is frozen as evidence in ``fractured_wilds_petri_w4_topologies_2026``.
This isolated module imports only its low-level raster/material primitives and
replaces rejected dominant carriers.  It remains unwired and makes no owner
acceptance claim.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np

from engine.expansions import fractured_wilds_petri_w4_topologies_2026 as w4


S, X, Y, U, V, TAU = w4.S, w4.X, w4.Y, w4.U, w4.V, w4.TAU
Grammar = w4.Grammar
_f, _n = w4._f, w4._n
_soft_gt, _band, _phase_band = w4._soft_gt, w4._band, w4._phase_band
_edge, _dilate, _erode, _halo = w4._edge, w4._dilate, w4._erode, w4._halo
_curve, _line, _circle, _ellipse, _bezier = (
    w4._curve, w4._line, w4._circle, w4._ellipse, w4._bezier
)
_sites, _literal_spec, _finish = w4._sites, w4._literal_spec, w4._finish


def _blank():
    return np.zeros((S, S), np.float32)


def _rotate(point, angle):
    c, s = np.cos(angle), np.sin(angle)
    p = np.asarray(point, np.float32)
    return np.asarray((p[0] * c - p[1] * s, p[0] * s + p[1] * c), np.float32)


# ---------------------------------------------------------------------------
# Lime Culture: two edge-fed genealogies; no weighted radial cells remain.


def w5_lime_culture() -> Grammar:
    parent = _blank(); mutant = _blank(); old_trunks = _blank(); young_twigs = _blank()
    septa = _blank(); buds = _blank(); mutation_nodes = _blank(); bridges = _blank()
    lysis = _blank(); nutrient = _blank()
    tips = []

    def grow(start, angle, bank, lineage):
        frontier = [(np.asarray(start, np.float32), float(angle), int(lineage))]
        for depth in range(9):
            next_frontier = []
            for node, heading, code in frontier:
                length = 25.0 + 3.0 * ((code + depth) % 5)
                bend = .16 * np.sin(code * .83 + depth * 1.27)
                end = node + length * np.asarray((np.cos(heading + bend),
                                                  np.sin(heading + bend)), np.float32)
                path = _bezier(node,
                               node + (end - node) * .30 + _rotate((0, 3 + code % 4), heading),
                               node + (end - node) * .72 + _rotate((0, -3 - depth % 3), heading),
                               end, 24)
                body = parent if bank == "A" else mutant
                _curve(body, path, 7 if depth < 2 else 5)
                _curve(old_trunks if depth < 3 else young_twigs, path,
                       3 if depth < 2 else 2)
                midpoint = path[len(path) // 2]
                tangent = end - node
                tangent /= np.linalg.norm(tangent) + 1.0e-6
                normal = np.asarray((-tangent[1], tangent[0]))
                if (code + depth) % 3 == 0:
                    _line(septa, midpoint - normal * 4, midpoint + normal * 4, 2)
                if depth >= 3 and (code + depth) % 2 == 0:
                    _circle(buds, end, 3 + code % 2, 2)
                if depth == 4 and code % 3 == 1:
                    _circle(mutation_nodes, end, 5, 2)
                    bank = "B" if bank == "A" else "A"
                if (code + depth) % 7 == 2:
                    _line(lysis, midpoint - tangent * 4, midpoint + tangent * 4, 2)
                tips.append((end.copy(), bank, depth))
                if depth < 8 and -38 < end[0] < 550 and -38 < end[1] < 550:
                    spread = .31 - .018 * depth
                    next_frontier.append((end, heading - spread, code * 2 + 1))
                    if (code + depth) % 4 != 0:
                        next_frontier.append((end, heading + spread * .91, code * 2 + 2))
            frontier = next_frontier

    seeds = [((-18, 58), .20, "A"), ((-22, 216), -.08, "B"),
             ((-18, 410), -.22, "A"), ((530, 112), np.pi - .17, "B"),
             ((536, 334), np.pi + .10, "A"), ((126, -20), 1.31, "B"),
             ((356, 532), -1.69, "A")]
    for i, (start, angle, bank) in enumerate(seeds):
        grow(start, angle, bank, 17 + i * 23)

    for i in range(7, len(tips) - 13, 37):
        a, bank_a, _ = tips[i]
        candidates = [(np.linalg.norm(a - b), b, bank_b)
                      for b, bank_b, _ in tips[i + 5:i + 45]
                      if bank_b != bank_a]
        if candidates:
            dist, b, _ = min(candidates, key=lambda row: row[0])
            if dist < 46:
                _curve(bridges, _bezier(a, a + (7, -5), b + (-7, 5), b, 20), 2)
    active_tips = _dilate(buds, 1)
    nutrient[:] = _f(_halo(np.maximum(parent, mutant), 4.0)
                     - .38 * np.maximum(parent, mutant))
    masks = dict(parent_lineage_bodies=parent, mutant_lineage_bodies=mutant,
                 old_transport_trunks=old_trunks, young_division_twigs=young_twigs,
                 transverse_division_septa=septa, active_daughter_buds=active_tips,
                 mutation_switch_nodes=mutation_nodes,
                 conjugation_bridges=bridges, lysis_breaks=lysis,
                 depleted_nutrient_channels=nutrient)
    banks = dict(parent_lineage_bodies="A", mutant_lineage_bodies="B",
                 old_transport_trunks="A", young_division_twigs="B",
                 transverse_division_septa="A", active_daughter_buds="B",
                 mutation_switch_nodes="B", conjugation_bridges="N",
                 lysis_breaks="N", depleted_nutrient_channels="N")
    spec = _literal_spec(
        masks,
        (("parent_lineage_bodies", 204), ("mutant_lineage_bodies", 30),
         ("old_transport_trunks", 246), ("transverse_division_septa", 154),
         ("lysis_breaks", 82)),
        (("parent_lineage_bodies", 74), ("mutant_lineage_bodies", 186),
         ("depleted_nutrient_channels", 236), ("active_daughter_buds", 36),
         ("conjugation_bridges", 128)),
        (("parent_lineage_bodies", 20), ("mutant_lineage_bodies", 224),
         ("young_division_twigs", 246), ("mutation_switch_nodes", 166),
         ("active_daughter_buds", 104)),
    )
    return _finish(masks, banks, _halo(np.maximum(old_trunks, young_twigs), 3.2)
                   + .31 * mutation_nodes, spec)


# ---------------------------------------------------------------------------
# Violet Garden: one transport graph with loops, pruning and differentiated nodes.


def w5_violet_garden() -> Grammar:
    points = _sites(238, phase=29, margin=-8)
    delta = points[:, None, :] - points[None, :, :]
    distance = np.linalg.norm(delta, axis=2)
    np.fill_diagonal(distance, np.inf)
    edges = set()
    for i in range(len(points)):
        for j in np.argsort(distance[i])[:4]:
            a, b = sorted((i, int(j)))
            if distance[a, b] < 62:
                edges.add((a, b))
    primary = _blank(); secondary = _blank(); abandoned = _blank(); loops = _blank()
    junctions = _blank(); spores = _blank(); sheaths = _blank(); scars = _blank()
    pumps = _blank(); droplets = _blank()
    degrees = np.zeros(len(points), np.int16)
    for a, b in edges:
        degrees[a] += 1; degrees[b] += 1
    for index, (a, b) in enumerate(sorted(edges)):
        p, q = points[a], points[b]
        tangent = q - p
        normal = np.asarray((-tangent[1], tangent[0]))
        normal /= np.linalg.norm(normal) + 1.0e-6
        bow = normal * (3.0 + (a * 7 + b * 11) % 9) * (-1 if (a + b) & 1 else 1)
        path = _bezier(p, p + .31 * tangent + bow, p + .69 * tangent - .6 * bow, q, 26)
        if (a * 13 + b * 7) % 11 == 0:
            _curve(abandoned, path, 2)
        elif (a + b) % 4 == 0:
            _curve(secondary, path, 2)
        else:
            _curve(primary, path, 5 if max(degrees[a], degrees[b]) >= 6 else 3)
        if (a * 5 + b * 3) % 17 == 2:
            _curve(loops, path, 2)
    for i, p in enumerate(points):
        if degrees[i] >= 4:
            _circle(junctions, p, 3 + degrees[i] % 3, -1)
            _circle(pumps, p, 6 + degrees[i] % 2, 2)
        elif degrees[i] <= 2 or i % 11 == 2:
            _circle(scars, p, 3, 2)
        if i % 9 == 4:
            _circle(spores, p, 3 + i % 2, 2)
        if i % 13 == 5:
            _ellipse(droplets, p + (4, -3), (4, 2), i * 23, -1)
    sheaths[:] = _f(_dilate(np.maximum(primary, secondary), 3)
                    - _dilate(np.maximum(primary, secondary), 1))
    substrate = _f(1.0 - _dilate(np.maximum.reduce((primary, secondary, abandoned)), 4))
    masks = dict(high_flow_transport_veins=primary, low_flow_side_veins=secondary,
                 abandoned_transport_links=abandoned, anastomosis_loops=loops,
                 multiway_pump_junctions=junctions, fruiting_spore_nodes=spores,
                 mucous_tube_sheaths=sheaths, sealed_dead_end_scars=scars,
                 peristaltic_pump_rings=pumps, nutrient_droplets=droplets,
                 depleted_garden_substrate=substrate)
    banks = dict(high_flow_transport_veins="A", low_flow_side_veins="B",
                 abandoned_transport_links="N", anastomosis_loops="B",
                 multiway_pump_junctions="A", fruiting_spore_nodes="B",
                 mucous_tube_sheaths="B", sealed_dead_end_scars="N",
                 peristaltic_pump_rings="A", nutrient_droplets="B",
                 depleted_garden_substrate="N")
    spec = _literal_spec(
        masks,
        (("high_flow_transport_veins", 224), ("low_flow_side_veins", 42),
         ("multiway_pump_junctions", 246), ("peristaltic_pump_rings", 156),
         ("sealed_dead_end_scars", 84)),
        (("depleted_garden_substrate", 238), ("high_flow_transport_veins", 74),
         ("abandoned_transport_links", 196), ("nutrient_droplets", 36),
         ("sealed_dead_end_scars", 132)),
        (("depleted_garden_substrate", 16), ("low_flow_side_veins", 214),
         ("mucous_tube_sheaths", 246), ("fruiting_spore_nodes", 166),
         ("anastomosis_loops", 104)),
    )
    return _finish(masks, banks, _halo(np.maximum(primary, secondary), 3.4)
                   + .27 * junctions, spec)


# ---------------------------------------------------------------------------
# Lime Diatom: varied small valve fragments; no card-scale crossing rails.


def w5_lime_diatom() -> Grammar:
    bodies_a = _blank(); bodies_b = _blank(); raphes = _blank(); striae = _blank()
    costae = _blank(); nodules = _blank(); pores = _blank(); girdles = _blank()
    chips = _blank(); overlap = _blank()
    centres = _sites(148, phase=43, margin=-12)
    for i, centre in enumerate(centres):
        angle = (i * 2.399963 + .53 * np.sin(i * .71)) % (2 * np.pi)
        length = 9.0 + (i * 11) % 11
        width = 3.0 + (i * 7) % 4
        tangent = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
        normal = np.asarray((-tangent[1], tangent[0]), np.float32)
        start, end = centre - tangent * length, centre + tangent * length
        bow = normal * (2.0 + (i % 5)) * (-1 if i & 1 else 1)
        path = _bezier(start, start + tangent * length * .66 + bow,
                       end - tangent * length * .66 - .6 * bow, end, 33)
        body = bodies_a if i % 3 else bodies_b
        _curve(body, path, min(8, int(2 * width)))
        _curve(raphes, path, 2)
        left_edge, right_edge = [], []
        for k in range(3, 30, 3):
            p = path[k]
            t = path[min(32, k + 2)] - path[max(0, k - 2)]
            t /= np.linalg.norm(t) + 1.0e-6
            n = np.asarray((-t[1], t[0]))
            span = width * (.72 + .16 * np.sin(np.pi * k / 32.0))
            _line(striae, p - n * span, p + n * span, 2)
            if (k // 4 + i) % 4 == 0:
                _line(costae, p - n * (span + 1.5), p + n * (span + 1.5), 3)
            left_edge.append(p - n * span)
            right_edge.append(p + n * span)
        _curve(girdles, left_edge, 2); _curve(girdles, right_edge, 2)
        _circle(nodules, path[16], 2 + i % 2, -1)
        for p in (path[3], path[-4]):
            _circle(pores, p, 2, 2)
        if i % 5 == 1:
            _line(chips, path[8], path[11] + normal * 3, 2)
        if i % 7 == 3:
            _ellipse(overlap, centre + normal * 4, (5, 2), np.degrees(angle), 2)
    medium = _f(1.0 - _dilate(np.maximum(bodies_a, bodies_b), 2))
    masks = dict(pennate_valve_bodies=bodies_a, conjugate_valve_bodies=bodies_b,
                 central_raphe_slits=raphes, transverse_silica_striae=striae,
                 reinforced_costae=costae, central_nodules=nodules,
                 terminal_pores=pores, girdle_band_edges=girdles,
                 chipped_valve_sectors=chips, valve_overlap_saddles=overlap,
                 culture_medium=medium)
    banks = dict(pennate_valve_bodies="A", conjugate_valve_bodies="B",
                 central_raphe_slits="B", transverse_silica_striae="A",
                 reinforced_costae="B", central_nodules="A", terminal_pores="B",
                 girdle_band_edges="N", chipped_valve_sectors="N",
                 valve_overlap_saddles="B", culture_medium="N")
    spec = _literal_spec(
        masks,
        (("pennate_valve_bodies", 216), ("conjugate_valve_bodies", 30),
         ("reinforced_costae", 246), ("central_nodules", 156),
         ("chipped_valve_sectors", 82)),
        (("culture_medium", 238), ("pennate_valve_bodies", 78),
         ("terminal_pores", 34), ("valve_overlap_saddles", 188),
         ("chipped_valve_sectors", 132)),
        (("culture_medium", 16), ("conjugate_valve_bodies", 224),
         ("transverse_silica_striae", 246), ("girdle_band_edges", 166),
         ("central_raphe_slits", 104)),
    )
    return _finish(masks, banks, _halo(np.maximum(bodies_a, bodies_b), 2.7)
                   + .29 * striae, spec)


BUILDERS: Mapping[str, Callable[[], Grammar]] = dict(w4.BUILDERS)
BUILDERS.update({
    "fpe_lime_culture": w5_lime_culture,
    "fpe_violet_garden": w5_violet_garden,
    "fpe_lime_diatom": w5_lime_diatom,
})
HUES = w4.HUES
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
    levels = (.18, .32, .47, .61, .74, .86, .96, .55, .27, .68, .81)
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
