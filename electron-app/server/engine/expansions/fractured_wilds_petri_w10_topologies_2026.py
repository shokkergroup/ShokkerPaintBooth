# -*- coding: utf-8 -*-
"""WR-P10 one-finish Petri repair: hierarchical Physarum Violet Garden.

W5's uniform nearest-neighbour paver and W9's solid DLA stripe are both gone.
This candidate constructs an unequal transport hierarchy: one minimum-energy
arterial tree, a few explicit anastomosis loops, fine branch-originating
exploratory tubes, pump chambers and peristaltic septa.  Every secondary mark
is attached to the recorded transport anatomy; no scatter/noise layer exists.

SPB-WILDS 2026-08-24, WR-P10. Isolated candidate; not production-wired and no
owner acceptance is claimed.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np

from engine.expansions import fractured_wilds_petri_w9_topologies_2026 as w9


w8, w7, w6, w5, w4 = w9.w8, w9.w7, w9.w6, w9.w5, w9.w4
S, X, Y, U, V, TAU = w4.S, w4.X, w4.Y, w4.U, w4.V, w4.TAU
Grammar = w4.Grammar
_f, _n = w4._f, w4._n
_soft_gt, _band, _phase_band = w4._soft_gt, w4._band, w4._phase_band
_edge, _dilate, _erode, _halo = w4._edge, w4._dilate, w4._erode, w4._halo
_curve, _line, _circle, _ellipse, _bezier = (
    w4._curve, w4._line, w4._circle, w4._ellipse, w4._bezier
)
_literal_spec, _finish = w4._literal_spec, w4._finish


def _blank():
    return np.zeros((S, S), np.float32)


def _minimum_spanning_edges(points):
    points = np.asarray(points, np.float32)
    delta = points[:, None, :] - points[None, :, :]
    distance = np.linalg.norm(delta, axis=2)
    visited = {0}
    edges = []
    while len(visited) < len(points):
        best = None
        for a in visited:
            for b in range(len(points)):
                if b in visited:
                    continue
                candidate = (float(distance[a, b]), int(a), int(b))
                if best is None or candidate < best:
                    best = candidate
        _d, a, b = best
        visited.add(b)
        edges.append((a, b))
    return edges, distance


def w10_violet_garden() -> Grammar:
    # Thirty-seven nutrient sites make a hierarchy, not a uniform micro-pave.
    points = w4._sites(37, phase=211, margin=-18)
    tree_edges, distance = _minimum_spanning_edges(points)
    degrees = np.zeros(len(points), np.int16)
    for a, b in tree_edges:
        degrees[a] += 1; degrees[b] += 1

    # Add only eight short non-tree links, chosen by a deterministic global
    # energy ordering. These are biologically meaningful anastomoses.
    tree_set = {tuple(sorted(edge)) for edge in tree_edges}
    candidates = []
    for a in range(len(points)):
        for b in range(a + 1, len(points)):
            if (a, b) in tree_set or distance[a, b] > 112:
                continue
            score = distance[a, b] * (1.0 + .09 * ((a * 7 + b * 11) % 5))
            candidates.append((score, a, b))
    loop_edges = [(a, b) for _score, a, b in sorted(candidates)[:8]]
    for a, b in loop_edges:
        degrees[a] += 1; degrees[b] += 1

    primary = _blank(); secondary = _blank(); loop_tubes = _blank()
    exploratory = _blank(); peristaltic = _blank(); pump_chambers = _blank()
    sealed_ends = _blank(); spore_bulbs = _blank(); lumen = _blank()
    all_paths = []

    for edge_index, (a, b) in enumerate(tree_edges + loop_edges):
        p, q = points[a], points[b]
        tangent = q - p
        length = np.linalg.norm(tangent) + 1.0e-6
        unit = tangent / length
        normal = np.asarray((-unit[1], unit[0]), np.float32)
        bow = normal * (5.0 + (a * 5 + b * 3) % 15) * (-1 if (a + b) & 1 else 1)
        path = _bezier(p, p + .30 * tangent + bow,
                       p + .69 * tangent - .55 * bow, q, 44)
        all_paths.append((path, a, b, edge_index >= len(tree_edges)))
        if edge_index >= len(tree_edges):
            _curve(loop_tubes, path, 3)
        elif max(degrees[a], degrees[b]) >= 4 or length > 86:
            _curve(primary, path, 7)
        else:
            _curve(secondary, path, 4)
        _curve(lumen, path, 2)

        # Contractile septa cross their own tube at irregular recorded samples.
        for k in range(7 + edge_index % 4, 40, 10 + edge_index % 3):
            t = path[min(43, k + 2)] - path[max(0, k - 2)]
            t /= np.linalg.norm(t) + 1.0e-6
            n = np.asarray((-t[1], t[0]))
            _line(peristaltic, path[k] - n * 4, path[k] + n * 4, 2)

        # Fine exploratory branches originate from the transport wall and
        # curve away; none is an independent low-discrepancy stroke.
        if edge_index < len(tree_edges):
            for branch_index, k in enumerate((9, 17, 26, 35)):
                if (edge_index + branch_index) % 3 == 0:
                    continue
                t = path[min(43, k + 2)] - path[max(0, k - 2)]
                t /= np.linalg.norm(t) + 1.0e-6
                n = np.asarray((-t[1], t[0]))
                side = -1.0 if (edge_index + branch_index) & 1 else 1.0
                extent = 13.0 + ((edge_index * 7 + k) % 17)
                start = path[k] + n * side * 3.0
                end = start + n * side * extent + t * (6.0 * np.sin(edge_index + k))
                branch = _bezier(start, start + n * side * 6,
                                 end - t * 5 + n * side * 2, end, 22)
                _curve(exploratory, branch, 2)

    for i, point in enumerate(points):
        if degrees[i] >= 3:
            _ellipse(pump_chambers, point, (6 + degrees[i], 4 + degrees[i] // 2),
                     i * 29, 3)
        if degrees[i] == 1:
            _circle(sealed_ends, point, 3 + i % 2, 2)
            if i % 3:
                _ellipse(spore_bulbs, point + (3 - i % 7, i % 5 - 2),
                         (4 + i % 3, 3), i * 17, 2)

    transport = np.maximum.reduce((primary, secondary, loop_tubes, exploratory))
    outer_membrane = _f(_dilate(transport, 3) - _dilate(transport, 1))
    streaming_sheath = _f(_halo(transport, 4.1) + .27 * _dilate(transport, 2))
    collision_knots = _f(_dilate(primary, 2) * _dilate(loop_tubes, 2)
                         + .48 * pump_chambers)
    depleted_medium = _f(1.0 - _dilate(streaming_sheath, 1))

    masks = dict(
        high_flow_primary_arteries=primary,
        low_flow_secondary_tubes=secondary,
        anastomosis_loop_tubes=loop_tubes,
        branch_origin_exploratory_tubes=exploratory,
        central_streaming_lumens=lumen,
        transverse_peristaltic_septa=peristaltic,
        differentiated_pump_chambers=pump_chambers,
        sealed_transport_ends=sealed_ends,
        fruiting_spore_bulbs=spore_bulbs,
        living_outer_membranes=outer_membrane,
        cytoplasmic_streaming_sheaths=streaming_sheath,
        artery_loop_collision_knots=collision_knots,
        depleted_garden_medium=depleted_medium,
    )
    banks = dict(
        high_flow_primary_arteries="A", low_flow_secondary_tubes="B",
        anastomosis_loop_tubes="B", branch_origin_exploratory_tubes="A",
        central_streaming_lumens="B", transverse_peristaltic_septa="A",
        differentiated_pump_chambers="A", sealed_transport_ends="N",
        fruiting_spore_bulbs="B", living_outer_membranes="B",
        cytoplasmic_streaming_sheaths="A", artery_loop_collision_knots="B",
        depleted_garden_medium="N",
    )
    spec = _literal_spec(
        masks,
        (("high_flow_primary_arteries", 226), ("low_flow_secondary_tubes", 54),
         ("anastomosis_loop_tubes", 126), ("central_streaming_lumens", 246),
         ("differentiated_pump_chambers", 178),
         ("branch_origin_exploratory_tubes", 94),
         ("sealed_transport_ends", 76), ("artery_loop_collision_knots", 252)),
        (("depleted_garden_medium", 252), ("high_flow_primary_arteries", 28),
         ("low_flow_secondary_tubes", 164), ("central_streaming_lumens", 104),
         ("transverse_peristaltic_septa", 18),
         ("cytoplasmic_streaming_sheaths", 202),
         ("fruiting_spore_bulbs", 92), ("sealed_transport_ends", 154)),
        (("depleted_garden_medium", 18), ("high_flow_primary_arteries", 82),
         ("low_flow_secondary_tubes", 216), ("anastomosis_loop_tubes", 246),
         ("living_outer_membranes", 232),
         ("transverse_peristaltic_septa", 152),
         ("fruiting_spore_bulbs", 252), ("artery_loop_collision_knots", 118)),
    )
    tone = (_n(streaming_sheath) + .28 * peristaltic + .25 * pump_chambers
            + .19 * exploratory)
    return _finish(masks, banks, tone, spec)


BUILDERS: Mapping[str, Callable[[], Grammar]] = dict(w9.BUILDERS)
BUILDERS["fpe_violet_garden"] = w10_violet_garden
HUES = w9.HUES
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
    levels = (.18, .32, .47, .61, .74, .86, .96, .55, .27, .68, .81, .42, .90)
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
