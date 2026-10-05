# -*- coding: utf-8 -*-
"""WR-B4 owner-eye replacement topologies for twenty isolated Bloom finishes.

This module is art-only and intentionally unwired.  WR-B3 remains intact as
rejection history.  Every constructor below owns a different full-domain
biological topology, explicit named A/B paint regions, and stable per-feature
M/R/Cc recipes.  Low-level raster helpers are shared; no card receives a shared
carrier, tile, grain, row, grid, hub, icon pack, or parallel ribbon substrate.

Work resolution is 512 square.  Drawn walls, veins, ribs, seams, pores, hooks,
fibres, and lips use 2--8 work-pixel strokes (8--32 pixels at 2048 output).
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Callable, Dict, Mapping, Sequence, Tuple

import cv2
import numpy as np


S = 512
Y, X = np.mgrid[0:S, 0:S].astype(np.float32)


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    tone: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]


def _f(a):
    return np.clip(np.asarray(a, np.float32), 0.0, 1.0)


def _n(a):
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    if hi - lo < 1.0e-7:
        return np.zeros_like(a)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _blank():
    return np.zeros((S, S), np.float32)


def _edge(a, width=1):
    u = _f(a)
    k = np.ones((2 * int(width) + 1,) * 2, np.uint8)
    return _f(cv2.dilate(u, k) - cv2.erode(u, k))


def _halo(a, sigma=2.0):
    u = _f(a)
    return _f(cv2.GaussianBlur(u, (0, 0), float(sigma)) - 0.18 * u)


def _dilate(a, radius=1):
    k = np.ones((2 * int(radius) + 1,) * 2, np.uint8)
    return _f(cv2.dilate(_f(a), k))


def _erode(a, radius=1):
    k = np.ones((2 * int(radius) + 1,) * 2, np.uint8)
    return _f(cv2.erode(_f(a), k))


def _curve(mask, points, width=2, value=1.0, closed=False):
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    if len(pts) >= 2:
        cv2.polylines(mask, [pts], bool(closed), float(value), int(width), cv2.LINE_AA)


def _line(mask, a, b, width=2, value=1.0):
    cv2.line(mask, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
             float(value), int(width), cv2.LINE_AA)


def _circle(mask, center, radius, width=2, value=1.0):
    cv2.circle(mask, tuple(np.rint(center).astype(int)), max(1, int(round(radius))),
               float(value), int(width), cv2.LINE_AA)


def _ellipse(mask, center, axes, angle=0.0, width=2, value=1.0,
             start=0.0, end=360.0):
    cv2.ellipse(mask, tuple(np.rint(center).astype(int)),
                tuple(np.maximum(1, np.rint(axes).astype(int))), float(angle),
                float(start), float(end), float(value), int(width), cv2.LINE_AA)


def _poly(mask, points, width=2, fill=False, value=1.0):
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    if fill:
        cv2.fillPoly(mask, [pts], float(value), cv2.LINE_AA)
    else:
        cv2.polylines(mask, [pts], True, float(value), int(width), cv2.LINE_AA)


def _bezier(p0, p1, p2, p3, count=128):
    t = np.linspace(0.0, 1.0, int(count), dtype=np.float32)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, np.float32) for p in (p0, p1, p2, p3))
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


def _open_arc(center, rx, ry, start, sweep, count=48):
    a = np.linspace(start, start + sweep, int(count), dtype=np.float32)
    cx, cy = center
    return np.c_[cx + rx * np.cos(a), cy + ry * np.sin(a)]


def _distance_to_ink(ink):
    return cv2.distanceTransform((np.asarray(ink) < 0.18).astype(np.uint8),
                                 cv2.DIST_L2, 5).astype(np.float32)


def _halton(index, base):
    result, factor, n = 0.0, 1.0, int(index)
    while n > 0:
        factor /= float(base)
        result += factor * (n % base)
        n //= base
    return result


def _sites(count, phase, margin=10.0):
    span = S - 2.0 * float(margin)
    out = []
    for i in range(1, int(count) + 1):
        hx = (_halton(i + 7 * phase, 2) + 0.073 * np.sin(i * 1.71 + phase)) % 1.0
        hy = (_halton(i + 11 * phase, 3) + 0.061 * np.cos(i * 1.37 + phase)) % 1.0
        out.append((margin + span * hx, margin + span * hy))
    return np.asarray(out, np.float32)


def _power_cells(points, weights=None):
    pts = np.asarray(points, np.float32)
    if weights is None:
        weights = np.zeros(len(pts), np.float32)
    best = np.full((S, S), np.inf, np.float32)
    second = np.full((S, S), np.inf, np.float32)
    label = np.zeros((S, S), np.int16)
    for i, ((px, py), weight) in enumerate(zip(pts, np.asarray(weights, np.float32))):
        d = (X - px) ** 2 + (Y - py) ** 2 - float(weight)
        take = d < best
        second = np.where(take, best, np.minimum(second, d))
        label = np.where(take, i, label)
        best = np.where(take, d, best)
    return label, _n(np.maximum(second - best, 0.0)), _n(best)


def _cell_edges(label, width=1):
    lab = np.asarray(label)
    edge = np.zeros(lab.shape, np.float32)
    edge[:, 1:] = np.maximum(edge[:, 1:], lab[:, 1:] != lab[:, :-1])
    edge[1:, :] = np.maximum(edge[1:, :], lab[1:, :] != lab[:-1, :])
    return _dilate(edge, width)


def _channel(base: float, masks: Mapping[str, np.ndarray], components):
    """Low-level blend only; every builder supplies its own literal recipe."""
    out = np.full((S, S), float(base), np.float32)
    for name, target in components:
        u = _f(masks[name])
        out = out * (1.0 - u) + float(target) * u
    return np.clip(out, 0.0, 255.0).astype(np.float32)


def _literal_spec(masks: Mapping[str, np.ndarray], metal, rough, coat):
    return (_channel(8.0, masks, metal),
            _channel(220.0, masks, rough),
            _channel(10.0, masks, coat))


def _finish(masks: Mapping[str, np.ndarray], banks: Mapping[str, str],
            tone, explicit_spec) -> Grammar:
    if len(masks) < 7:
        raise ValueError("WR-B4 lazy grammar: fewer than seven causal marks")
    if set(masks) != set(banks):
        raise ValueError("WR-B4 bank topology mismatch")
    rows = []
    for name, mask in masks.items():
        u = _f(mask)
        shoulder = cv2.dilate(u, np.ones((2, 2), np.uint8))
        u = np.maximum(u, 0.70 * shoulder)
        if float(u.std()) < 0.0015:
            raise ValueError(f"WR-B4 flat causal mark {name!r}")
        owner = banks[name]
        if owner not in {"A", "B", "N"}:
            raise ValueError(f"WR-B4 bad owner {owner!r}")
        rows.append((name, u.astype(np.float32), owner))
    if not ({"A", "B"} <= {owner for _name, _mask, owner in rows}):
        raise ValueError("WR-B4 grammar lacks explicit A/B anatomy")
    if not (isinstance(explicit_spec, tuple) and len(explicit_spec) == 3):
        raise ValueError("WR-B4 builder must supply literal M/R/Cc arrays")
    spec = tuple(np.clip(np.asarray(ch, np.float32), 0.0, 255.0)
                 for ch in explicit_spec)
    if any(ch.shape != (S, S) for ch in spec):
        raise ValueError("WR-B4 spec shape mismatch")
    return Grammar(tuple(rows), _n(tone).astype(np.float32), spec)


def owner_unions(grammar: Grammar):
    a = np.zeros((S, S), np.float32)
    b = np.zeros_like(a)
    for _name, mask, owner in grammar.marks:
        if owner == "A":
            a = np.maximum(a, mask)
        elif owner == "B":
            b = np.maximum(b, mask)
    return a, b


# 01 — multi-front crozier vascular delta; no rows and no common root.
def w4_magenta_whorl():
    # WR-B4 pass 3: a context-sensitive fern-venation L-system.  The pass-2
    # straight spans still read as railway ladders.  Twenty-four boundary
    # microfronts now grow in short causal steps, fork locally, and terminate
    # or graft on encounter; there is no persistent crop-spanning trunk lane.
    rachis, fronts, pinnae, capillaries = (_blank() for _ in range(4))
    mature_lamina, young_lamina, grafts, hooks = (_blank() for _ in range(4))
    scars, pores, lips = (_blank() for _ in range(3))
    initial = []
    for i in range(6):
        q = 36.0 + i * 88.0 + 9.0 * np.sin(i * 1.41)
        initial.extend(((np.asarray((-3.0, q), np.float32), .03, 4 * i),
                        (np.asarray((S + 2.0, (q * 1.27 + 47) % S), np.float32),
                         np.pi + .11, 4 * i + 1),
                        (np.asarray(((q * .73 + 91) % S, -3.0), np.float32),
                         np.pi / 2 + .09, 4 * i + 2),
                        (np.asarray(((q * 1.11 + 23) % S, S + 2.0), np.float32),
                         -np.pi / 2 - .07, 4 * i + 3)))
    fronts_state = [(p, a, seed, seed * 13 + 1, 0)
                    for p, a, seed in initial]
    buckets = {}
    points = []
    seeds = []

    def record(point, seed):
        idx = len(points)
        points.append(point.copy())
        seeds.append(seed)
        key = (int(np.floor(point[0] / 9.0)), int(np.floor(point[1] / 9.0)))
        buckets.setdefault(key, []).append(idx)

    for p, _a, seed in initial:
        record(p, seed)
    for generation in range(48):
        next_fronts = []
        for p, angle, seed, code, age in fronts_state:
            bend = (.19 * np.sin(code * .73 + generation * .61)
                    + .08 * np.sin((p[0] - p[1]) / 39.0))
            local = angle + bend
            step = 4.8 + ((code * 7 + generation * 5) % 6) * .43
            end = p + step * np.asarray((np.cos(local), np.sin(local)), np.float32)
            if not (-5 <= end[0] <= S + 4 and -5 <= end[1] <= S + 4):
                continue
            bx, by = int(np.floor(end[0] / 9.0)), int(np.floor(end[1] / 9.0))
            encounter = None
            for yy in range(by - 1, by + 2):
                for xx in range(bx - 1, bx + 2):
                    for idx in buckets.get((xx, yy), ()):
                        if seeds[idx] != seed and np.linalg.norm(points[idx] - end) < 6.2:
                            encounter = points[idx]
                            break
                    if encounter is not None:
                        break
                if encounter is not None:
                    break
            target = rachis if (seed + generation // 7) % 2 == 0 else fronts
            _line(target, p, end, 2 + (generation < 7))
            tangent = np.asarray((np.cos(local), np.sin(local)), np.float32)
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            if (code + generation) % 3 == 0:
                side = -1.0 if code % 2 else 1.0
                length = 4.0 + ((code + generation * 3) % 7)
                tip = end + side * normal * length + tangent * 2
                _curve(pinnae if (code + seed) % 3 else capillaries,
                       _bezier(end, end + tangent * 2,
                               end + side * normal * length * .7, tip, 12), 2)
            if (code + 2 * generation) % 17 == 0:
                _curve(hooks, _open_arc(end + normal * 3, 3, 2,
                                        local, 3.4, 12), 2)
            if (code + generation) % 19 == 0:
                _circle(pores, end, 2, 2)
            if encounter is not None:
                _line(grafts, end, encounter, 2)
                continue
            record(end, seed)
            next_fronts.append((end, local, seed, code * 3 + 1, age + 1))
            if (generation >= 5 and generation < 34
                    and (code + generation * 5) % 8 == 0
                    and len(next_fronts) < 760):
                fork = .42 + .07 * ((code + seed) % 3)
                next_fronts.append((end, local + (-fork if code % 2 else fork),
                                    seed, code * 3 + 2, age + 1))
        fronts_state = next_fronts[:760]
        if not fronts_state:
            break
    mature_lamina[:] = _f(.88 * _dilate(np.maximum(rachis, grafts), 3)
                          + .62 * _dilate(pinnae, 2))
    young_lamina[:] = _f(.88 * _dilate(np.maximum(fronts, capillaries), 3)
                         + .58 * _dilate(hooks, 2))
    scars[:] = _edge(np.maximum(mature_lamina, grafts), 1)
    lips[:] = _edge(young_lamina, 1) * (1.0 - pores)
    masks = dict(mature_rachides=rachis, advancing_rachides=fronts,
                 mature_lamina=mature_lamina, young_lamina=young_lamina,
                 fine_pinnae=pinnae, lamina_capillaries=capillaries,
                 graft_bridges=grafts, crozier_hooks=hooks,
                 scar_seams=scars, junction_pores=pores, overlap_lips=lips)
    banks = dict(mature_rachides="A", advancing_rachides="B",
                 mature_lamina="A", young_lamina="B", fine_pinnae="A",
                 lamina_capillaries="B", graft_bridges="A",
                 crozier_hooks="B", scar_seams="N", junction_pores="N",
                 overlap_lips="B")
    spec = _literal_spec(
        masks,
        (("mature_lamina", 238), ("mature_rachides", 252),
         ("fine_pinnae", 208), ("graft_bridges", 178),
         ("scar_seams", 142), ("junction_pores", 110),
         ("young_lamina", 22), ("advancing_rachides", 48),
         ("lamina_capillaries", 76), ("crozier_hooks", 96),
         ("overlap_lips", 124)),
        (("mature_lamina", 52), ("mature_rachides", 24),
         ("fine_pinnae", 82), ("graft_bridges", 112),
         ("scar_seams", 148), ("junction_pores", 202),
         ("young_lamina", 224), ("advancing_rachides", 188),
         ("lamina_capillaries", 156), ("crozier_hooks", 116),
         ("overlap_lips", 72)),
        (("mature_lamina", 28), ("mature_rachides", 12),
         ("fine_pinnae", 58), ("graft_bridges", 88),
         ("scar_seams", 118), ("junction_pores", 136),
         ("young_lamina", 252), ("advancing_rachides", 232),
         ("lamina_capillaries", 206), ("crozier_hooks", 180),
         ("overlap_lips", 150)))
    return _finish(masks, banks,
                   _distance_to_ink(np.maximum(mature_lamina, young_lamina))
                   + .19 * X - .11 * Y, spec)


# 02 — four-edge liana mesh with forced graft continuity.
def w4_leafvine_drape():
    # A deterministic space-colonisation vine, not six decorative ropes.  Four
    # crop roots compete for a nonuniform target canopy; live tips fork only
    # where their own nearby targets demand it, then foreign root lineages
    # physically graft when they meet.  This is the sole colonisation process
    # in Bloom W4.
    cambium, young_vines, grafts, blade_ribs = (_blank() for _ in range(4))
    tendrils, racemes, nodes_mask, bark_scars = (_blank() for _ in range(4))
    capillary_web, mature_sheet, young_sheet = (_blank() for _ in range(3))
    targets = _sites(920, 23, margin=-3.0)
    # Break low-discrepancy straight alignments without noise: the displacement
    # is an explicit canopy warp and is applied once to the attraction targets.
    targets[:, 0] += 13.0 * np.sin(targets[:, 1] / 41.0)
    targets[:, 1] += 11.0 * np.sin(targets[:, 0] / 57.0 + .8)
    root_rows = (
        ((-4, 54), (1.0, .16)), ((-4, 254), (1.0, -.11)),
        ((-4, 454), (1.0, .09)), ((S + 3, 112), (-1.0, .13)),
        ((S + 3, 306), (-1.0, -.18)), ((S + 3, 482), (-1.0, -.08)),
        ((76, -4), (.12, 1.0)), ((258, -4), (-.16, 1.0)),
        ((448, -4), (.08, 1.0)), ((42, S + 3), (.14, -1.0)),
        ((226, S + 3), (-.11, -1.0)), ((414, S + 3), (.17, -1.0)),
    )
    nodes = [np.asarray(p, np.float32) for p, _direction in root_rows]
    ancestry = list(range(len(root_rows)))
    directions = [np.asarray(direction, np.float32)
                  / (np.linalg.norm(direction) + 1.0e-6)
                  for _p, direction in root_rows]
    segments = []
    remaining = targets.copy()
    for generation in range(104):
        if len(remaining) == 0:
            break
        cloud = np.asarray(nodes, np.float32)
        d2 = ((remaining[:, None, :] - cloud[None, :, :]) ** 2).sum(axis=2)
        nearest = np.argmin(d2, axis=1)
        keep = np.min(d2, axis=1) > 6.2 ** 2
        nearest, remaining = nearest[keep], remaining[keep]
        if len(remaining) == 0:
            break
        births = []
        for node_i in np.unique(nearest):
            assigned = remaining[nearest == node_i]
            delta = assigned - nodes[int(node_i)]
            delta /= np.linalg.norm(delta, axis=1, keepdims=True) + 1.0e-6
            direction = delta.mean(axis=0) + .58 * directions[int(node_i)]
            direction += .12 * np.asarray((np.sin(node_i * 1.7 + generation * .31),
                                           np.cos(node_i * 1.1 - generation * .27)))
            direction /= np.linalg.norm(direction) + 1.0e-6
            step = 4.8 + ((int(node_i) * 7 + generation * 3) % 5) * .37
            endpoint = nodes[int(node_i)] + direction * step
            if not (-10 <= endpoint[0] <= S + 10 and -10 <= endpoint[1] <= S + 10):
                continue
            births.append((int(node_i), endpoint, direction))
        if not births:
            break
        for parent, endpoint, direction in births:
            child = len(nodes)
            nodes.append(endpoint)
            ancestry.append(ancestry[parent])
            directions.append(direction)
            segments.append((parent, child, generation))
            target = cambium if generation < 28 else young_vines
            _line(target, nodes[parent], endpoint, 2)
    cloud = np.asarray(nodes, np.float32)
    # Foreign-lineage encounters become literal grafts, not arbitrary chords.
    for i in range(4, len(nodes), 5):
        dist = np.linalg.norm(cloud - cloud[i], axis=1)
        candidates = [j for j in np.argsort(dist)[1:14]
                      if ancestry[j] != ancestry[i] and dist[j] < 14.0]
        if candidates:
            j = int(candidates[0])
            _line(grafts, cloud[i], cloud[j], 2)
            _circle(nodes_mask, .5 * (cloud[i] + cloud[j]), 2, 2)
    # Terminal and late-generation anatomy is irregularly inherited from the
    # graph itself; no row, endpoint icon pack, or universal overlay exists.
    for q, (_parent, child, generation) in enumerate(segments[::3]):
        p = cloud[child]
        t = directions[child]
        n = np.asarray((-t[1], t[0]), np.float32)
        side = -1.0 if (child + generation) % 2 else 1.0
        _line(blade_ribs, p, p + side * n * (7 + child % 7) + t * 3, 2)
        if q % 3 == 0:
            _curve(tendrils, _open_arc(p + side * n * 6, 3 + q % 3,
                                      3 + child % 2, .37 * q, 3.7, 15), 2)
        if q % 4 == 0:
            tip = p - side * n * (6 + q % 5) + t * 4
            _line(racemes, p, tip, 2)
            _circle(racemes, tip, 2, 2)
    mature_sheet[:] = _f(.92 * _dilate(cambium, 4) + .68 * _dilate(grafts, 3))
    young_sheet[:] = _f(.86 * _dilate(young_vines, 3)
                        + .60 * _dilate(blade_ribs, 2))
    bark_scars[:] = _edge(np.maximum(mature_sheet, grafts), 1)
    capillary_web[:] = _halo(np.maximum.reduce((young_vines, blade_ribs, racemes)), 1.15)
    masks = dict(woody_cambium=cambium, live_tip_network=young_vines,
                 mature_lamina_sheet=mature_sheet, young_lamina_sheet=young_sheet,
                 forced_cross_grafts=grafts, blade_ribs=blade_ribs,
                 tendril_coils=tendrils, raceme_channels=racemes,
                 graft_nodes=nodes_mask, bark_scars=bark_scars,
                 lamina_capillary_web=capillary_web)
    banks = dict(woody_cambium="A", live_tip_network="B",
                 mature_lamina_sheet="A", young_lamina_sheet="B",
                 forced_cross_grafts="A", blade_ribs="B", tendril_coils="B",
                 raceme_channels="B", graft_nodes="N", bark_scars="A",
                 lamina_capillary_web="N")
    spec = _literal_spec(
        masks,
        (("mature_lamina_sheet", 232), ("woody_cambium", 252),
         ("forced_cross_grafts", 208), ("bark_scars", 172),
         ("graft_nodes", 126), ("young_lamina_sheet", 22),
         ("live_tip_network", 44), ("blade_ribs", 70),
         ("tendril_coils", 96), ("raceme_channels", 112),
         ("lamina_capillary_web", 148)),
        (("mature_lamina_sheet", 58), ("woody_cambium", 28),
         ("forced_cross_grafts", 84), ("bark_scars", 122),
         ("graft_nodes", 188), ("young_lamina_sheet", 228),
         ("live_tip_network", 202), ("blade_ribs", 168),
         ("tendril_coils", 132), ("raceme_channels", 94),
         ("lamina_capillary_web", 150)),
        (("mature_lamina_sheet", 24), ("woody_cambium", 12),
         ("forced_cross_grafts", 52), ("bark_scars", 88),
         ("graft_nodes", 134), ("young_lamina_sheet", 252),
         ("live_tip_network", 236), ("blade_ribs", 212),
         ("tendril_coils", 184), ("raceme_channels", 160),
         ("lamina_capillary_web", 112)))
    return _finish(masks, banks, _distance_to_ink(
        np.maximum.reduce((mature_sheet, young_sheet, grafts)))
        + .13 * X + .17 * Y, spec)


# 03 — anisotropic callose labyrinth; no repeated capsules.
def w4_butter_pollen():
    # High-frequency anisotropic callose: the W4 first board used 60--100 px
    # loops.  These warped phases resolve to 2--8 work-pixel walls and unequal
    # microchambers while remaining one explicit, non-tiled field process.
    wx = X + 9.0 * np.sin(Y / 47.0) + 4.0 * np.sin((X + Y) / 89.0)
    wy = Y + 7.0 * np.sin(X / 53.0 + .8) - 3.0 * np.sin((X - 2 * Y) / 97.0)
    u = (np.sin(.286 * wx + .107 * wy + .73 * np.sin(wy / 23.0))
         + .81 * np.sin(.173 * wx - .319 * wy + .54 * np.cos(wx / 31.0))
         + .59 * np.cos(.397 * wx + .131 * wy))
    v = (np.cos(.211 * wx + .347 * wy + .61 * np.sin((wx - wy) / 37.0))
         - .64 * np.sin(.421 * wy - .083 * wx))
    callose = _f((.20 - np.abs(u)) / .105 + .30)
    membranes = _f((.18 - np.abs(u - .47 * np.sin(v))) / .10 + .27)
    septa = _f((.14 - np.abs(v)) / .085 + .23) * _dilate(callose, 1)
    rupture = _f((.12 - np.abs(u + .76)) / .085 + .21) * (v > -.31)
    pressure = _edge(_dilate(np.maximum(callose, membranes), 2), 1)
    laminations = _halo(np.maximum(callose, septa), 1.4)
    pores, collars, fissures = _blank(), _blank(), _blank()
    pore_points = _sites(92, 89, margin=4.0)
    for i, p in enumerate(pore_points):
        _circle(pores, p, 2 + (i % 2), 2)
        _ellipse(collars, p, (3 + i % 3, 2 + (i * 2) % 3),
                 angle=(i * 29) % 180, width=2, start=28, end=326)
        direction = np.asarray((5 * np.cos(i * .91), 5 * np.sin(i * .91)))
        _line(fissures, np.asarray(p) - direction,
              np.asarray(p) + direction * 1.7, 2)
    masks = dict(callose_tube_walls=callose, pressurized_lumen_membranes=membranes,
                 local_septa=septa, rupture_fronts=rupture,
                 pressure_collars=pressure, callose_laminations=laminations,
                 germ_pore_canals=pores, broken_pore_collars=collars,
                 branching_fissures=fissures)
    banks = dict(callose_tube_walls="A", pressurized_lumen_membranes="B",
                 local_septa="A", rupture_fronts="B", pressure_collars="N",
                 callose_laminations="A", germ_pore_canals="B",
                 broken_pore_collars="N", branching_fissures="B")
    spec = _literal_spec(
        masks,
        (("callose_tube_walls", 250), ("local_septa", 214),
         ("callose_laminations", 176), ("pressure_collars", 126),
         ("broken_pore_collars", 98), ("pressurized_lumen_membranes", 22),
         ("rupture_fronts", 48), ("germ_pore_canals", 76),
         ("branching_fissures", 36)),
        (("callose_tube_walls", 32), ("local_septa", 68),
         ("callose_laminations", 110), ("pressure_collars", 148),
         ("broken_pore_collars", 196), ("pressurized_lumen_membranes", 224),
         ("rupture_fronts", 82), ("germ_pore_canals", 128),
         ("branching_fissures", 174)),
        (("callose_tube_walls", 16), ("local_septa", 54),
         ("callose_laminations", 86), ("pressure_collars", 132),
         ("broken_pore_collars", 118), ("pressurized_lumen_membranes", 252),
         ("rupture_fronts", 228), ("germ_pore_canals", 188),
         ("branching_fissures", 212)))
    return _finish(masks, banks, u + .37 * v + .21 * callose
                   - .17 * membranes, spec)


# 04 — edge-cropped petal shear fronts with local, nonparallel vein systems.
def w4_pink_rose():
    # Overlapping edge-cropped petal territories replace six giant ribbons.
    # Each territory is a tapered, nonparallel biological sheet with a literal
    # centre vein; local overlap creates the fold skeleton and causal A/B faces.
    upper, under, veins, tears = (_blank() for _ in range(4))
    fold_lips, cross_ribs, pores, scars, fringe = (_blank() for _ in range(5))
    overlap_count = np.zeros((S, S), np.float32)
    for j in range(144):
        side = j % 4
        slot = j // 4
        q = (19.0 + slot * 31.7 + 13.0 * np.sin(j * 1.31)) % S
        if side == 0:
            start, base = np.asarray((-5.0, q), np.float32), 0.0
        elif side == 1:
            start, base = np.asarray((S + 4.0, q), np.float32), np.pi
        elif side == 2:
            start, base = np.asarray((q, -5.0), np.float32), np.pi / 2
        else:
            start, base = np.asarray((q, S + 4.0), np.float32), -np.pi / 2
        angle = base + .46 * np.sin(j * 2.17) + .13 * np.sin(slot * .73)
        length = 68.0 + ((j * 37 + slot * 11) % 111)
        direction = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
        normal0 = np.asarray((-direction[1], direction[0]), np.float32)
        end = start + direction * length + normal0 * (9 * np.sin(j * .91))
        centre = _bezier(start,
                         start + direction * length * .32 + normal0 * (8 + j % 9),
                         start + direction * length * .71 - normal0 * (5 + j % 7),
                         end, 34)
        tangent = np.gradient(centre, axis=0)
        tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1.0e-6
        normals = np.c_[-tangent[:, 1], tangent[:, 0]]
        u = np.linspace(0.0, 1.0, len(centre), dtype=np.float32)
        profile = np.maximum(np.sin(np.pi * u), 0.0) ** .72
        half_width = ((3.0 + (j % 5)) * (1.0 - .58 * u)
                      + (5.0 + ((j * 3) % 7)) * profile)
        left = centre + normals * half_width[:, None]
        right = centre - normals * half_width[:, None]
        polygon = np.vstack((left, right[::-1]))
        territory = _blank()
        _poly(territory, polygon, fill=True, value=.68 + .06 * (j % 5))
        target = upper if ((j * 17 + slot) % 9) < 4 else under
        target[:] = np.maximum(target, territory)
        overlap_count += (territory > .2).astype(np.float32)
        _curve(veins if j % 3 else cross_ribs, centre, 2)
        for k in (9 + j % 4, 19 + (j * 2) % 5, 27 + j % 3):
            p = centre[k]
            t = tangent[k]
            n = normals[k] * (-1 if (j + k) % 2 else 1)
            tip = p + n * (4 + (j + k) % 7) + t * 2
            _curve(cross_ribs if j % 3 else veins,
                   _bezier(p, p + t * 2, p + n * 4, tip, 10), 2)
        if j % 9 == 0:
            p, n = centre[22], normals[22]
            _line(tears, p - n * 3, p + n * 5, 2)
        if j % 13 == 0:
            _circle(pores, centre[15], 2, 2)
    fold_lips[:] = _edge(_f((overlap_count - 1.0) / 1.2), 1)
    scars[:] = _edge(np.maximum(upper, under), 1)
    fringe[:] = _halo(np.maximum(veins, tears), 1.05)
    masks = dict(exposed_petal_faces=upper, recessed_underfold_faces=under,
                 branching_petal_veins=veins, irregular_tears=tears,
                 fold_lips=fold_lips, cross_rib_tributaries=cross_ribs,
                 tissue_pores=pores, healed_overlap_scars=scars,
                 cuticle_fringe=fringe)
    banks = dict(exposed_petal_faces="A", recessed_underfold_faces="B",
                 branching_petal_veins="A", irregular_tears="B",
                 fold_lips="N", cross_rib_tributaries="B", tissue_pores="N",
                 healed_overlap_scars="A", cuticle_fringe="B")
    spec = _literal_spec(
        masks,
        (("exposed_petal_faces", 246), ("branching_petal_veins", 218),
         ("healed_overlap_scars", 174), ("fold_lips", 126),
         ("tissue_pores", 94), ("recessed_underfold_faces", 18),
         ("irregular_tears", 54), ("cross_rib_tributaries", 82),
         ("cuticle_fringe", 42)),
        (("exposed_petal_faces", 46), ("branching_petal_veins", 84),
         ("healed_overlap_scars", 124), ("fold_lips", 28),
         ("tissue_pores", 158), ("recessed_underfold_faces", 214),
         ("irregular_tears", 176), ("cross_rib_tributaries", 102),
         ("cuticle_fringe", 68)),
        (("exposed_petal_faces", 22), ("branching_petal_veins", 58),
         ("healed_overlap_scars", 96), ("fold_lips", 138),
         ("tissue_pores", 112), ("recessed_underfold_faces", 248),
         ("irregular_tears", 224), ("cross_rib_tributaries", 188),
         ("cuticle_fringe", 208)))
    return _finish(masks, banks, _n(overlap_count) + .31 * upper
                   + .69 * under, spec)


# 05 — fused reef skeleton grown from three off-canvas origins.
def w4_coral_cluster():
    # Four antler lineages grow inward, bifurcate to microscopic twigs, and
    # fuse at their nearest encounters.  Unlike the rejected three isolated
    # tree icons, every lineage spans a crop edge and joins one reef graph.
    old_cortex, live_growth, antler_forks, bridges = (_blank() for _ in range(4))
    split_cups, polyp_tufts, pores, scars, marrow = (_blank() for _ in range(5))
    old_sheet, live_sheet = _blank(), _blank()
    roots = (((-18, 52), .16), ((-18, 226), -.08), ((-18, 418), .11),
             ((530, 84), 3.04), ((530, 278), 3.29), ((530, 462), 3.08),
             ((72, -18), 1.38), ((252, -18), 1.52), ((438, -18), 1.73),
             ((96, 530), -1.42), ((304, 530), -1.73), ((478, 530), -1.91))
    lineage_nodes = [[] for _ in roots]
    terminal_rows = []
    for root_i, (root, angle) in enumerate(roots):
        queue = [(np.asarray(root, np.float32), float(angle), 98.0, 0, 1)]
        while queue:
            p, a, length, depth, branch_code = queue.pop(0)
            centre_pull = np.asarray((256.0, 256.0), np.float32) - p
            centre_angle = np.arctan2(centre_pull[1], centre_pull[0])
            # Early growth enters the crop; late growth retains local antler
            # direction and therefore does not collapse to a visible hub.
            blend = .24 * max(0.0, 1.0 - depth / 4.0)
            vx = (1.0 - blend) * np.cos(a) + blend * np.cos(centre_angle)
            vy = (1.0 - blend) * np.sin(a) + blend * np.sin(centre_angle)
            local_angle = np.arctan2(vy, vx) + .14 * np.sin(
                branch_code * 1.31 + root_i * .77 + depth)
            end = p + length * np.asarray((np.cos(local_angle),
                                            np.sin(local_angle)), np.float32)
            side = np.asarray((-np.sin(local_angle), np.cos(local_angle)), np.float32)
            path = _bezier(p, p + .31 * (end - p) + side * (5 + depth),
                           p + .69 * (end - p) - side * (4 + root_i), end, 38)
            _curve(old_cortex if depth < 3 else live_growth, path,
                   4 if depth < 2 else (3 if depth < 4 else 2))
            lineage_nodes[root_i].append(end)
            if depth >= 4:
                terminal_rows.append((root_i, end, local_angle, branch_code))
            if depth < 6:
                deltas = (-.54 - .045 * ((branch_code + root_i) % 3),
                          .48 + .052 * ((depth + branch_code) % 4))
                for child_i, delta in enumerate(deltas):
                    shrink = .68 if child_i == 0 else .625
                    queue.append((end, local_angle + delta, length * shrink,
                                  depth + 1, branch_code * 2 + child_i + 1))
            # Sparse nonrepeating polyp tissue grows from causal segment age.
            for qi, q in enumerate((.24, .49, .73)):
                if (branch_code + qi + depth) % 3:
                    continue
                point = path[int(q * (len(path) - 1))]
                twig = side * (5 + (branch_code + qi) % 7)
                _line(polyp_tufts, point, point + twig, 2)
                if (branch_code + qi) % 4 == 0:
                    _circle(pores, point + twig, 2, 2)
    # Exactly one closest fusion to each neighbouring lineage closes the reef;
    # shorter secondary encounters add local loops without arbitrary chords.
    for left in range(len(roots)):
        right = (left + 1) % len(roots)
        aa = np.asarray(lineage_nodes[left], np.float32)
        bb = np.asarray(lineage_nodes[right], np.float32)
        d2 = ((aa[:, None, :] - bb[None, :, :]) ** 2).sum(axis=2)
        order = np.argsort(d2, axis=None)
        made = 0
        for flat in order:
            i, j = np.unravel_index(int(flat), d2.shape)
            if made and d2[i, j] > 48.0 ** 2:
                break
            a, b = aa[i], bb[j]
            chord = b - a
            normal = np.asarray((-chord[1], chord[0]), np.float32)
            normal /= np.linalg.norm(normal) + 1.0e-6
            _curve(bridges, _bezier(a, a + .27 * chord + normal * 6,
                                    a + .73 * chord - normal * 5, b, 26), 2)
            made += 1
            if made >= 3:
                break
    for i, (_root, tip, angle, code) in enumerate(terminal_rows):
        if i % 3 == 0:
            _curve(split_cups, _open_arc(tip, 3 + code % 4, 3 + i % 3,
                                         angle - 1.4, 3.2, 16), 2)
        if i % 7 == 0:
            _circle(pores, tip, 2, 2)
    old_sheet[:] = _f(.88 * _dilate(old_cortex, 5) + .62 * _dilate(bridges, 3))
    live_sheet[:] = _f(.88 * _dilate(live_growth, 3)
                       + .64 * _dilate(polyp_tufts, 2))
    antler_forks[:] = _edge(np.maximum(old_sheet, live_sheet), 1)
    scars[:] = _edge(np.maximum(bridges, split_cups), 1)
    marrow[:] = _halo(np.maximum(old_cortex, bridges), 1.35)
    masks = dict(calcified_cortex=old_cortex, live_growth_tips=live_growth,
                 calcified_reef_sheet=old_sheet, live_polyp_sheet=live_sheet,
                 antler_fork_seams=antler_forks, fused_skeletal_bridges=bridges,
                 split_cup_lips=split_cups, irregular_polyp_tufts=polyp_tufts,
                 cortical_pores=pores, growth_scars=scars, marrow_channels=marrow)
    banks = dict(calcified_cortex="A", live_growth_tips="B",
                 calcified_reef_sheet="A", live_polyp_sheet="B",
                 antler_fork_seams="A", fused_skeletal_bridges="A",
                 split_cup_lips="B", irregular_polyp_tufts="B",
                 cortical_pores="N", growth_scars="N", marrow_channels="A")
    spec = _literal_spec(
        masks,
        (("calcified_reef_sheet", 236), ("calcified_cortex", 252),
         ("antler_fork_seams", 218), ("fused_skeletal_bridges", 184),
         ("marrow_channels", 154),
         ("cortical_pores", 116), ("growth_scars", 92),
         ("live_polyp_sheet", 20), ("live_growth_tips", 46),
         ("split_cup_lips", 72), ("irregular_polyp_tufts", 94)),
        (("calcified_reef_sheet", 54), ("calcified_cortex", 28),
         ("antler_fork_seams", 74), ("fused_skeletal_bridges", 108),
         ("marrow_channels", 152),
         ("cortical_pores", 202), ("growth_scars", 126),
         ("live_polyp_sheet", 228), ("live_growth_tips", 196),
         ("split_cup_lips", 142), ("irregular_polyp_tufts", 98)),
        (("calcified_reef_sheet", 24), ("calcified_cortex", 10),
         ("antler_fork_seams", 42), ("fused_skeletal_bridges", 78),
         ("marrow_channels", 112),
         ("cortical_pores", 142), ("growth_scars", 106),
         ("live_polyp_sheet", 252), ("live_growth_tips", 232),
         ("split_cup_lips", 204), ("irregular_polyp_tufts", 178)))
    return _finish(masks, banks,
                   _distance_to_ink(np.maximum(old_sheet, live_sheet))
                   + .14 * X + .09 * Y, spec)


# 06 — hierarchical marquetry faults and botanical shards, no oval cells.
def w4_butter_mosaic():
    # Recursive botanical cleavage replaces the pass-1 crossing arc skeleton.
    # Every leaf shard descends from an actual unequal split of its parent;
    # the resulting 2--8 px faults are crop-cut on every edge and have no
    # repeated oval cell, common centre, rectangular hull, lane or grid.
    lineage_a, lineage_b, primary, secondary = (_blank() for _ in range(4))
    shard_veins, resin, lips, tears = (_blank() for _ in range(4))
    pores, bridges, splinters = (_blank() for _ in range(3))

    def clip_half(poly, normal, offset, positive):
        poly = np.asarray(poly, np.float32)
        out = []
        for i, cur in enumerate(poly):
            prev = poly[i - 1]
            dc = float(np.dot(cur, normal) - offset)
            dp = float(np.dot(prev, normal) - offset)
            cur_in = dc >= 0 if positive else dc <= 0
            prev_in = dp >= 0 if positive else dp <= 0
            if cur_in != prev_in:
                t = dp / (dp - dc + 1.0e-12)
                out.append(prev + t * (cur - prev))
            if cur_in:
                out.append(cur)
        return np.asarray(out, np.float32)

    root = np.asarray(((-8, -8), (S + 8, -8),
                       (S + 8, S + 8), (-8, S + 8)), np.float32)
    leaves = []
    stack = [(root, 0, 1, 0)]
    split_index = 0
    while stack:
        poly, depth, lineage, ancestry = stack.pop()
        area = abs(float(cv2.contourArea(poly)))
        if depth >= 11 or area < 112.0:
            leaves.append((poly, lineage, ancestry))
            continue
        center = poly.mean(axis=0)
        centred = poly - center
        covariance = centred.T @ centred / max(1, len(poly))
        values, vectors = np.linalg.eigh(covariance)
        long_axis = vectors[:, int(np.argmax(values))]
        angle = (np.arctan2(long_axis[1], long_axis[0])
                 + .27 * np.sin(split_index * 1.73 + depth * .91
                                + ancestry * .037)) % np.pi
        normal = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
        projection = poly @ normal
        lo, hi = float(projection.min()), float(projection.max())
        # Unequal but bounded cleavage prevents both regular tiling and slivers.
        fraction = .46 + .07 * np.sin(split_index * 1.83 + depth * .91)
        offset = lo + fraction * (hi - lo)
        first = clip_half(poly, normal, offset, False)
        second = clip_half(poly, normal, offset, True)
        split_index += 1
        if len(first) < 3 or len(second) < 3:
            leaves.append((poly, lineage, ancestry))
            continue
        # The cut itself is recorded at its causal hierarchy depth.
        tangent = np.asarray((-normal[1], normal[0]), np.float32)
        shared = np.concatenate((first, second), axis=0)
        shared = shared[np.abs(shared @ normal - offset) < 0.025]
        if len(shared) >= 2:
            along = shared @ tangent
            a, b = shared[int(np.argmin(along))], shared[int(np.argmax(along))]
            _line(primary if depth < 5 else secondary, a, b,
                  3 if depth < 4 else 2)
        stack.append((second, depth + 1, 1 - lineage,
                      (ancestry * 2 + 1) % 4093))
        stack.append((first, depth + 1, lineage,
                      (ancestry * 2 + 2) % 4093))

    for i, (poly, lineage, ancestry) in enumerate(leaves):
        if len(poly) < 3:
            continue
        target = lineage_a if lineage == 0 else lineage_b
        value = .70 + .06 * ((ancestry * 7 + i * 3) % 5)
        _poly(target, poly, fill=True, value=value)
        _poly(resin, poly, width=2)
        center = poly.mean(axis=0)
        mids = .5 * (poly + np.roll(poly, -1, axis=0))
        if len(mids):
            first = mids[(ancestry + i) % len(mids)]
            second_mid = mids[(ancestry * 3 + i + 1) % len(mids)]
            _line(shard_veins, center, first, 2)
            if i % 3 == 0:
                _line(shard_veins, center, second_mid, 2)
        if i % 17 == 0:
            _line(tears, center + (-3, 2), center + (4, -3), 2)
        if i % 23 == 0:
            _circle(pores, center, 2, 2)
        if i % 31 == 0 and len(mids):
            _line(bridges, center, mids[(i * 5 + 2) % len(mids)], 2)
    lips[:] = _edge(np.maximum(lineage_a, lineage_b), 1)
    splinters[:] = _edge(_dilate(shard_veins, 1), 1)
    masks = dict(mature_botanical_shards=lineage_a,
                 young_botanical_shards=lineage_b,
                 primary_marquetry_faults=primary,
                 secondary_shard_faults=secondary,
                 internal_botanical_veins=shard_veins, resin_grout=resin,
                 folded_fault_lips=lips, tissue_tears=tears, shard_pores=pores,
                 healed_resin_bridges=bridges, edge_splinters=splinters)
    banks = dict(mature_botanical_shards="A", young_botanical_shards="B",
                 primary_marquetry_faults="A", secondary_shard_faults="B",
                 internal_botanical_veins="A", resin_grout="N",
                 folded_fault_lips="B", tissue_tears="B", shard_pores="N",
                 healed_resin_bridges="A", edge_splinters="B")
    spec = _literal_spec(
        masks,
        (("mature_botanical_shards", 232), ("primary_marquetry_faults", 252),
         ("internal_botanical_veins", 208), ("healed_resin_bridges", 174),
         ("resin_grout", 126), ("shard_pores", 102),
         ("young_botanical_shards", 22), ("secondary_shard_faults", 50),
         ("folded_fault_lips", 76), ("tissue_tears", 94),
         ("edge_splinters", 112)),
        (("mature_botanical_shards", 52), ("primary_marquetry_faults", 24),
         ("internal_botanical_veins", 78), ("healed_resin_bridges", 114),
         ("resin_grout", 164), ("shard_pores", 208),
         ("young_botanical_shards", 228), ("secondary_shard_faults", 194),
         ("folded_fault_lips", 152), ("tissue_tears", 118),
         ("edge_splinters", 88)),
        (("mature_botanical_shards", 22), ("primary_marquetry_faults", 10),
         ("internal_botanical_veins", 48), ("healed_resin_bridges", 84),
         ("resin_grout", 132), ("shard_pores", 116),
         ("young_botanical_shards", 252), ("secondary_shard_faults", 232),
         ("folded_fault_lips", 206), ("tissue_tears", 184),
         ("edge_splinters", 160)))
    return _finish(masks, banks,
                   lineage_a * .27 + lineage_b * .73
                   + _distance_to_ink(np.maximum(primary, secondary)), spec)


# 07 — dense warped exine foam with short adjacency only.
def w4_pink_pollen():
    # Microscopic exine foam.  The old 84 weighted cells were macro pavers;
    # 1,420 literal germ centres are solved in one exact nearest-seed transform
    # and then gently deformed as a single exine sheet.  No long chords or
    # shared field carrier are added.
    points = _sites(1420, 31, margin=-2.0)
    seed = np.ones((S, S), np.uint8)
    ip = np.rint(points).astype(np.int32)
    ip[:, 0] = np.clip(ip[:, 0], 0, S - 1)
    ip[:, 1] = np.clip(ip[:, 1], 0, S - 1)
    seed[ip[:, 1], ip[:, 0]] = 0
    depth, label = cv2.distanceTransformWithLabels(
        seed, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    map_x = _f(X / (S - 1)) * (S - 1)
    map_y = _f(Y / (S - 1)) * (S - 1)
    map_x = np.clip(map_x + 4.7 * np.sin(Y / 37.0)
                    + 2.1 * np.sin((X + Y) / 71.0), 0, S - 1).astype(np.float32)
    map_y = np.clip(map_y + 3.9 * np.sin(X / 43.0 + .7)
                    - 2.4 * np.sin((X - 2 * Y) / 83.0), 0, S - 1).astype(np.float32)
    label = cv2.remap(label.astype(np.float32), map_x, map_y,
                      cv2.INTER_NEAREST).astype(np.int32)
    depth = cv2.remap(depth.astype(np.float32), map_x, map_y,
                      cv2.INTER_LINEAR)
    walls = _cell_edges(label, 1)
    lineage = (label * 73 + (label // 11) * 29) % 17
    compressed = np.where(lineage < 8,
                          .72 + .055 * (lineage % 5), 0.0).astype(np.float32)
    stretched = np.where(lineage >= 8,
                         .70 + .05 * ((lineage + 2) % 6), 0.0).astype(np.float32)
    septa = _edge(walls, 1)
    rupture = walls * (((label * 19 + label // 7) % 9) < 3).astype(np.float32)
    fold_zone = (((label * 11 + label // 5) % 13) < 5).astype(np.float32)
    folds = _f(_dilate(walls, 3) - _dilate(walls, 1)) * fold_zone
    pores, collars, canals, calluses = _blank(), _blank(), _blank(), _blank()
    for i, p in enumerate(points[::13]):
        p = np.asarray((np.clip(p[0], 2, S - 3), np.clip(p[1], 2, S - 3)))
        _circle(pores, p, 2 + i % 2, 2)
        _ellipse(collars, p, (3 + i % 3, 2 + (i * 3) % 2),
                 angle=(i * 47) % 180, width=2, start=38, end=316)
        angle = i * 2.399963 + .31
        _line(canals, p, p + (5 + i % 5)
              * np.asarray([np.cos(angle), np.sin(angle)]), 2)
        if i % 4 == 0:
            _curve(calluses, _open_arc(p + (2, -1), 3 + i % 2, 2,
                                      angle, 3.4, 13), 2)
    masks = dict(compressed_exine_faces=compressed,
                 stretched_membrane_faces=stretched,
                 short_septal_walls=walls, septal_edge_lips=septa,
                 local_rupture_fronts=rupture, compression_fold_webs=folds,
                 germ_pores=pores, broken_pore_collars=collars,
                 short_pore_canals=canals, healed_calluses=calluses)
    banks = dict(compressed_exine_faces="A", stretched_membrane_faces="B",
                 short_septal_walls="N", septal_edge_lips="A",
                 local_rupture_fronts="B",
                 compression_fold_webs="A", germ_pores="B",
                 broken_pore_collars="N", short_pore_canals="A",
                 healed_calluses="N")
    spec = _literal_spec(
        masks,
        (("compressed_exine_faces", 242), ("compression_fold_webs", 210),
         ("short_pore_canals", 176), ("septal_edge_lips", 152),
         ("short_septal_walls", 126),
         ("broken_pore_collars", 104), ("healed_calluses", 144),
         ("stretched_membrane_faces", 20), ("local_rupture_fronts", 52),
         ("germ_pores", 82)),
        (("compressed_exine_faces", 42), ("compression_fold_webs", 78),
         ("short_pore_canals", 118), ("septal_edge_lips", 136),
         ("short_septal_walls", 162),
         ("broken_pore_collars", 206), ("healed_calluses", 96),
         ("stretched_membrane_faces", 226), ("local_rupture_fronts", 174),
         ("germ_pores", 132)),
        (("compressed_exine_faces", 18), ("compression_fold_webs", 48),
         ("short_pore_canals", 82), ("septal_edge_lips", 108),
         ("short_septal_walls", 138),
         ("broken_pore_collars", 112), ("healed_calluses", 98),
         ("stretched_membrane_faces", 252), ("local_rupture_fronts", 220),
         ("germ_pores", 188)))
    tone = ((label * 37 + label // 13 * 17) % 101).astype(np.float32) / 100.0
    return _finish(masks, banks, tone + .07 * _n(depth), spec)


# 08 — nonparallel xylem/phloem exchange network.
def w4_white_whorl():
    # Approximate Steiner transport forest over irregular terminals.  Prim
    # growth produces only short local links; selected non-tree neighbours form
    # true exchange loops.  This replaces seven giant hose-like Béziers and is
    # the only minimum-transport process in the W4 shelf.
    xylem, phloem, exchanges, valves = (_blank() for _ in range(4))
    frays, plates, pores, scar_lips = (_blank() for _ in range(4))
    xylem_sheet, phloem_sheet, sheaths = (_blank() for _ in range(3))
    interior = _sites(360, 53, margin=4.0)
    boundary = []
    for i in range(12):
        q = 12 + i * 43 + 7 * np.sin(i * 1.7)
        boundary.extend(((-5, q), (S + 4, (q * 1.37 + 61) % S),
                         ((q * 1.71 + 29) % S, -5),
                         ((q * .83 + 113) % S, S + 4)))
    points = np.vstack((np.asarray(boundary, np.float32), interior))
    count = len(points)
    selected = np.zeros(count, bool)
    selected[0] = True
    best = np.sum((points - points[0]) ** 2, axis=1)
    parent = np.zeros(count, np.int32)
    depth = np.zeros(count, np.int32)
    tree_edges = []
    for _ in range(count - 1):
        candidates = np.where(selected, np.inf, best)
        child = int(np.argmin(candidates))
        if not np.isfinite(candidates[child]):
            break
        selected[child] = True
        par = int(parent[child])
        depth[child] = depth[par] + 1
        tree_edges.append((par, child))
        d2 = np.sum((points - points[child]) ** 2, axis=1)
        improve = (~selected) & (d2 < best)
        parent[improve] = child
        best[improve] = d2[improve]
    tree_pairs = {tuple(sorted(edge)) for edge in tree_edges}
    for edge_i, (a_i, b_i) in enumerate(tree_edges):
        a, b = points[a_i], points[b_i]
        chord = b - a
        length = np.linalg.norm(chord)
        if length < 1.0:
            continue
        normal = np.asarray((-chord[1], chord[0]), np.float32) / length
        bend = normal * (2.0 + ((a_i * 7 + b_i * 3) % 7))
        path = _bezier(a, a + .34 * chord + bend,
                       a + .68 * chord - .7 * bend, b, 18)
        target = xylem if (depth[b_i] + b_i) % 3 else phloem
        _curve(target, path, 2 + (depth[b_i] % 2))
        if edge_i % 7 == 0:
            mid = path[9]
            tangent = path[11] - path[7]
            tangent /= np.linalg.norm(tangent) + 1.0e-6
            n = np.asarray((-tangent[1], tangent[0]), np.float32)
            _line(valves, mid - n * (3 + edge_i % 4),
                  mid + n * (4 + (edge_i // 3) % 4), 2)
        if edge_i % 19 == 0:
            _circle(pores, path[6], 2, 2)
    # Short alternate routes are local split/reunion events, never long chords.
    for i in range(count):
        d2 = np.sum((points - points[i]) ** 2, axis=1)
        for j in np.argsort(d2)[1:7]:
            pair = tuple(sorted((i, int(j))))
            if pair in tree_pairs or j <= i or d2[j] > 24.0 ** 2:
                continue
            if (i * 17 + int(j) * 11) % 13:
                continue
            a, b = points[i], points[int(j)]
            chord = b - a
            normal = np.asarray((-chord[1], chord[0]), np.float32)
            normal /= np.linalg.norm(normal) + 1.0e-6
            _curve(exchanges, _bezier(a, a + .3 * chord + normal * 3,
                                      a + .7 * chord - normal * 3, b, 14), 2)
            centre = .5 * (a + b)
            _poly(plates, (centre + (-3, 0), centre + (0, -3),
                           centre + (4, 1), centre + (0, 4)), 2)
            break
    degrees = np.zeros(count, np.int16)
    for a_i, b_i in tree_edges:
        degrees[a_i] += 1
        degrees[b_i] += 1
    for i in np.where(degrees == 1)[0][::3]:
        p = points[i]
        t = points[i] - points[parent[i]] if i else np.asarray((1, 0), np.float32)
        t /= np.linalg.norm(t) + 1.0e-6
        n = np.asarray((-t[1], t[0]), np.float32)
        _line(frays, p, p + t * 6 + n * 4, 2)
        _line(frays, p, p + t * 5 - n * 5, 2)
    xylem_sheet[:] = _f(.90 * _dilate(xylem, 4) + .58 * _dilate(exchanges, 2))
    phloem_sheet[:] = _f(.90 * _dilate(phloem, 4) + .62 * _dilate(frays, 2))
    sheaths[:] = _edge(np.maximum(xylem_sheet, phloem_sheet), 1)
    scar_lips[:] = _edge(np.maximum(exchanges, plates), 1)
    masks = dict(xylem_cables=xylem, phloem_cables=phloem,
                 xylem_transport_sheet=xylem_sheet,
                 phloem_transport_sheet=phloem_sheet,
                 cable_sheaths=sheaths, exchange_bridges=exchanges,
                 local_valves=valves, terminal_frays=frays,
                 crossover_plates=plates, vascular_pores=pores,
                 exchange_scar_lips=scar_lips)
    banks = dict(xylem_cables="A", phloem_cables="B",
                 xylem_transport_sheet="A", phloem_transport_sheet="B",
                 cable_sheaths="A", exchange_bridges="N",
                 local_valves="B", terminal_frays="B",
                 crossover_plates="N", vascular_pores="A",
                 exchange_scar_lips="B")
    spec = _literal_spec(
        masks,
        (("xylem_transport_sheet", 236), ("xylem_cables", 252),
         ("cable_sheaths", 214), ("vascular_pores", 182),
         ("exchange_bridges", 128),
         ("crossover_plates", 102), ("phloem_cables", 18),
         ("phloem_transport_sheet", 42), ("local_valves", 66),
         ("terminal_frays", 92),
         ("exchange_scar_lips", 42)),
        (("xylem_transport_sheet", 54), ("xylem_cables", 26),
         ("cable_sheaths", 76), ("vascular_pores", 116),
         ("exchange_bridges", 158),
         ("crossover_plates", 202), ("phloem_cables", 226),
         ("phloem_transport_sheet", 198), ("local_valves", 164),
         ("terminal_frays", 136),
         ("exchange_scar_lips", 184)),
        (("xylem_transport_sheet", 22), ("xylem_cables", 10),
         ("cable_sheaths", 48), ("vascular_pores", 78),
         ("exchange_bridges", 132),
         ("crossover_plates", 108), ("phloem_cables", 252),
         ("phloem_transport_sheet", 232), ("local_valves", 206),
         ("terminal_frays", 178),
         ("exchange_scar_lips", 208)))
    return _finish(masks, banks,
                   _distance_to_ink(np.maximum(xylem_sheet, phloem_sheet))
                   + .29 * xylem + .71 * phloem, spec)


# 09 — displaced connective tendon with changing filament-brush anatomy.
def w4_coral_stamen():
    # Dense Morse--Smale stamen tissue.  Watershed separatrices from one
    # asymmetric scalar anatomy replace the old tendon with evenly alternating
    # lollipops.  Faces, saddle sprays and dehiscence all descend from the same
    # causal field; no detached icon row or master axis remains.
    wx = X + 11.0 * np.sin(Y / 59.0) + 5.0 * np.sin((X + Y) / 101.0)
    wy = Y - 9.0 * np.sin(X / 67.0 + .4) + 4.0 * np.sin((2 * X - Y) / 113.0)
    scalar = (np.sin(.218 * wx + .097 * wy)
              + .71 * np.cos(.137 * wx - .263 * wy + .4)
              + .49 * np.sin(.337 * wx + .181 * wy + .7)
              + .31 * np.cos(.089 * wx + .419 * wy))
    norm_scalar = _n(scalar)
    z8 = np.clip(norm_scalar * 255, 0, 255).astype(np.uint8)
    minima = ((z8 == cv2.erode(z8, np.ones((5, 5), np.uint8)))
              & (z8 < np.percentile(z8, 43))).astype(np.uint8)
    marker_count, markers = cv2.connectedComponents(minima, 8)
    if marker_count < 8:
        raise ValueError("WR-B4 Morse-Smale field lacks locule minima")
    markers = markers.astype(np.int32) + 1
    markers[minima == 0] = 0
    image = cv2.cvtColor(z8, cv2.COLOR_GRAY2BGR)
    cv2.watershed(image, markers)
    connective = _dilate((markers == -1).astype(np.float32), 1)
    labels = np.maximum(markers, 1)
    lineage = (labels * 29 + labels // 7 * 13) % 19
    filament_a = np.where(lineage < 9,
                          .70 + .055 * (lineage % 5), 0.0).astype(np.float32)
    filament_b = np.where(lineage >= 9,
                          .72 + .05 * ((lineage + 2) % 5), 0.0).astype(np.float32)
    locule_walls = _edge(np.maximum(filament_a, filament_b), 1)
    gx = cv2.Sobel(norm_scalar, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(norm_scalar, cv2.CV_32F, 0, 1, ksize=3)
    dxx = cv2.Sobel(norm_scalar, cv2.CV_32F, 2, 0, ksize=3)
    dyy = cv2.Sobel(norm_scalar, cv2.CV_32F, 0, 2, ksize=3)
    dxy = cv2.Sobel(norm_scalar, cv2.CV_32F, 1, 1, ksize=3)
    determinant = dxx * dyy - dxy * dxy
    saddle = ((determinant < np.percentile(determinant, 31))
              & (np.hypot(gx, gy) < np.percentile(np.hypot(gx, gy), 62)))
    side_sprays = _dilate(saddle.astype(np.float32), 1) * (1.0 - connective)
    pollen_channels = _f(cv2.Canny(z8, 72, 148).astype(np.float32) / 255.0)
    folds = _edge(_dilate(connective, 2), 1)
    dehiscence = connective * (np.hypot(gx, gy)
                               > np.percentile(np.hypot(gx, gy), 66))
    pores = _blank()
    ys, xs = np.where(minima > 0)
    for i, (px, py) in enumerate(zip(xs[::7], ys[::7])):
        _circle(pores, (px, py), 2, 2)
    masks = dict(connective_separatrices=connective,
                 mature_filament_basins=filament_a,
                 young_filament_basins=filament_b,
                 micro_locule_walls=locule_walls,
                 pollen_channels=pollen_channels, lateral_sprays=side_sprays,
                 connective_folds=folds, pollen_pores=pores,
                 dehiscence_lips=dehiscence)
    banks = dict(connective_separatrices="A", mature_filament_basins="A",
                 young_filament_basins="B", micro_locule_walls="B",
                 pollen_channels="B", lateral_sprays="B",
                 connective_folds="N", pollen_pores="N",
                 dehiscence_lips="A")
    spec = _literal_spec(
        masks,
        (("mature_filament_basins", 238), ("connective_separatrices", 252),
         ("dehiscence_lips", 178), ("connective_folds", 128),
         ("pollen_pores", 96), ("young_filament_basins", 22),
         ("micro_locule_walls", 48), ("pollen_channels", 76),
         ("lateral_sprays", 88)),
        (("mature_filament_basins", 52), ("connective_separatrices", 24),
         ("dehiscence_lips", 118), ("connective_folds", 162),
         ("pollen_pores", 210), ("young_filament_basins", 226),
         ("micro_locule_walls", 94), ("pollen_channels", 142),
         ("lateral_sprays", 184)),
        (("mature_filament_basins", 22), ("connective_separatrices", 10),
         ("dehiscence_lips", 88), ("connective_folds", 134),
         ("pollen_pores", 112), ("young_filament_basins", 250),
         ("micro_locule_walls", 224), ("pollen_channels", 188),
         ("lateral_sprays", 206)))
    return _finish(masks, banks, norm_scalar + .31 * filament_a
                   + .69 * filament_b, spec)


# 10 — interdigitating cusp-wall thicket, not ellipses or a flower icon.
def w4_lilac_rose():
    # Pass 2 uses a microscopic full-frame cusp epidermis.  The old 58-site
    # board read as detached squiggle icons; 540 unequal sites make the shared
    # walls themselves the tissue without introducing filled polygon pavers.
    points = _sites(540, 41, margin=-5)
    walls_a, walls_b, cusps, thorn_ribs = (_blank() for _ in range(4))
    fold_lips, tears, faults, pores, capillaries = (_blank() for _ in range(5))
    for i, p in enumerate(points):
        d = np.sum((points - p) ** 2, axis=1)
        neighbors = np.argsort(d)[1:4]
        for rank, j in enumerate(neighbors[:2]):
            q = points[j]
            mid = .5 * (p + q)
            normal = np.asarray([-(q - p)[1], (q - p)[0]], np.float32)
            normal /= np.linalg.norm(normal) + 1.0e-6
            bend = normal * (3 + ((i * 13 + j * 5) % 7)) * (-1 if rank else 1)
            path = _bezier(p, .55 * p + .45 * mid + bend,
                           .45 * q + .55 * mid - bend, q, 34)
            _curve(walls_a if (i + j) % 2 else walls_b, path, 2)
        a = .37 * i
        tip1 = p + (5 + i % 5) * np.asarray([np.cos(a), np.sin(a)])
        tip2 = p + (5 + (i * 3) % 6) * np.asarray([np.cos(a + 2.2), np.sin(a + 2.2)])
        _curve(cusps, (tip1, p, tip2), 2)
        if i % 3 == 0:
            _line(thorn_ribs, p, p + (6 + i % 7) * np.asarray([np.cos(a + 1.1),
                                                                np.sin(a + 1.1)]), 2)
        if i % 11 == 0:
            _circle(pores, p, 2, 2)
        if i % 7 == 0:
            _line(tears, p + (-3, 2), p + (5, -4), 2)
    fold_lips[:] = _edge(np.maximum(walls_a, walls_b), 1)
    faults[:] = _dilate(cusps, 1)
    capillaries[:] = _halo(np.maximum(thorn_ribs, cusps), 1.1)
    masks = dict(convex_cusp_walls=walls_a, recessed_cusp_walls=walls_b,
                 shared_petal_cusps=cusps, thorn_ribs=thorn_ribs,
                 folded_wall_lips=fold_lips, epidermal_tears=tears,
                 vascular_faults=faults, cuticle_pores=pores,
                 lamina_capillaries=capillaries)
    banks = dict(convex_cusp_walls="A", recessed_cusp_walls="B",
                 shared_petal_cusps="N", thorn_ribs="A",
                 folded_wall_lips="B", epidermal_tears="B",
                 vascular_faults="A", cuticle_pores="N", lamina_capillaries="B")
    spec = _literal_spec(
        masks,
        (("convex_cusp_walls", 248), ("thorn_ribs", 218),
         ("vascular_faults", 182), ("cuticle_pores", 116),
         ("shared_petal_cusps", 136), ("recessed_cusp_walls", 18),
         ("folded_wall_lips", 52), ("epidermal_tears", 78),
         ("lamina_capillaries", 92)),
        (("convex_cusp_walls", 38), ("thorn_ribs", 72),
         ("vascular_faults", 108), ("cuticle_pores", 166),
         ("shared_petal_cusps", 202), ("recessed_cusp_walls", 224),
         ("folded_wall_lips", 88), ("epidermal_tears", 142),
         ("lamina_capillaries", 184)),
        (("convex_cusp_walls", 16), ("thorn_ribs", 48),
         ("vascular_faults", 84), ("cuticle_pores", 118),
         ("shared_petal_cusps", 138), ("recessed_cusp_walls", 252),
         ("folded_wall_lips", 222), ("epidermal_tears", 186),
         ("lamina_capillaries", 204)))
    return _finish(masks, banks,
                   _distance_to_ink(np.maximum(walls_a, walls_b))
                   + .31 * walls_a + .67 * walls_b, spec)


# 11 — four-edge recursive crown fused into one graph.
def w4_coral_vine():
    # Percolated micro-canopy: 1,800 unequal 5--8 px growth discs fuse before
    # their medial axis is extracted.  The output is one crop-spanning organism,
    # not a set of recursive tree crowns.  No other Bloom finish uses this
    # union/medial-axis process.
    points = _sites(1800, 67, margin=-4.0)
    canopy_u8 = np.zeros((S, S), np.uint8)
    for i, p in enumerate(points):
        radius = 5 + ((i * 11 + i // 7) % 4)
        cv2.circle(canopy_u8, tuple(np.rint(p).astype(int)), radius, 255, -1,
                   cv2.LINE_AA)
    canopy_u8 = cv2.morphologyEx(canopy_u8, cv2.MORPH_CLOSE,
                                 np.ones((3, 3), np.uint8), iterations=1)
    # Retain only the component that owns the largest biological canopy, then
    # fuse any near-touching satellites into it with one local closing pass.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        (canopy_u8 > 0).astype(np.uint8), 8)
    if count > 1:
        main = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        core = (labels == main).astype(np.uint8) * 255
        near = cv2.dilate(core, np.ones((7, 7), np.uint8))
        attach = ((near > 0) & (canopy_u8 > 0)).astype(np.uint8) * 255
        canopy_u8 = cv2.morphologyEx(np.maximum(core, attach), cv2.MORPH_CLOSE,
                                     np.ones((5, 5), np.uint8))
    work = (canopy_u8 > 0).astype(np.uint8)
    skeleton = np.zeros_like(work)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while cv2.countNonZero(work):
        opened = cv2.morphologyEx(work, cv2.MORPH_OPEN, element)
        skeleton = np.maximum(skeleton, work - opened)
        work = cv2.erode(work, element)
    skeleton_f = _dilate(skeleton.astype(np.float32), 1)
    distance = cv2.distanceTransform((canopy_u8 > 0).astype(np.uint8),
                                     cv2.DIST_L2, 5)
    mature_sheet = _f((distance - 3.3) / 2.2 + .5)
    live_sheet = _f((3.9 - distance) / 1.8 + .5) * (canopy_u8 > 0)
    lignified = skeleton_f * _f((distance - 3.0) / 1.6 + .5)
    live_twigs = skeleton_f * _f((4.4 - distance) / 1.8 + .5)
    boundary = _edge((canopy_u8 > 0).astype(np.float32), 1)
    neighbours = cv2.filter2D((skeleton > 0).astype(np.uint8), -1,
                              np.ones((3, 3), np.uint8))
    junctions = ((skeleton > 0) & (neighbours >= 4)).astype(np.float32)
    endpoints = ((skeleton > 0) & (neighbours == 2)).astype(np.uint8)
    grafts = _dilate(junctions, 2)
    nodes = _edge(grafts, 1)
    leaf_ribs = boundary * (1.0 - _dilate(grafts, 1))
    tendrils, racemes = _blank(), _blank()
    ys, xs = np.where(endpoints > 0)
    for i, (px, py) in enumerate(zip(xs[::4], ys[::4])):
        centre = np.asarray((px, py), np.float32)
        angle = i * 2.399963 + .37 * np.sin(i * .71)
        _curve(tendrils, _open_arc(centre, 3 + i % 3, 2 + (i // 3) % 3,
                                  angle, 3.5, 14), 2)
        if i % 3 == 0:
            tip = centre + (5 + i % 5) * np.asarray((np.cos(angle),
                                                      np.sin(angle)))
            _line(racemes, centre, tip, 2)
            _circle(racemes, tip, 2, 2)
    capillaries = _halo(np.maximum(live_twigs, leaf_ribs), 1.0)
    bark_lips = _edge(mature_sheet, 1)
    masks = dict(lignified_medial_limbs=lignified,
                 live_medial_twigs=live_twigs,
                 mature_percolated_canopy=mature_sheet,
                 live_canopy_membrane=live_sheet,
                 contact_graft_junctions=grafts, narrow_leaf_ribs=leaf_ribs,
                 tendril_coils=tendrils, twig_capillaries=capillaries,
                 graft_nodes=nodes, bark_overlap_lips=bark_lips,
                 raceme_channels=racemes)
    banks = dict(lignified_medial_limbs="A", live_medial_twigs="B",
                 mature_percolated_canopy="A", live_canopy_membrane="B",
                 contact_graft_junctions="A", narrow_leaf_ribs="B",
                 tendril_coils="B", twig_capillaries="B", graft_nodes="N",
                 bark_overlap_lips="A", raceme_channels="B")
    spec = _literal_spec(
        masks,
        (("mature_percolated_canopy", 236), ("lignified_medial_limbs", 252),
         ("contact_graft_junctions", 216), ("bark_overlap_lips", 182),
         ("graft_nodes", 126), ("live_canopy_membrane", 20),
         ("live_medial_twigs", 44), ("narrow_leaf_ribs", 70),
         ("tendril_coils", 72), ("twig_capillaries", 94),
         ("raceme_channels", 38)),
        (("mature_percolated_canopy", 54), ("lignified_medial_limbs", 26),
         ("contact_graft_junctions", 68), ("bark_overlap_lips", 112),
         ("graft_nodes", 158), ("live_canopy_membrane", 228),
         ("live_medial_twigs", 198), ("narrow_leaf_ribs", 164),
         ("tendril_coils", 138), ("twig_capillaries", 184),
         ("raceme_channels", 206)),
        (("mature_percolated_canopy", 22), ("lignified_medial_limbs", 10),
         ("contact_graft_junctions", 42), ("bark_overlap_lips", 82),
         ("graft_nodes", 132), ("live_canopy_membrane", 252),
         ("live_medial_twigs", 232), ("narrow_leaf_ribs", 208),
         ("tendril_coils", 194), ("twig_capillaries", 174),
         ("raceme_channels", 214)))
    return _finish(masks, banks, _n(distance) + .31 * mature_sheet
                   + .67 * live_sheet, spec)


# 12 — asymmetric off-crop locule cutaway with distinct internal fibre fields.
def w4_lilac_stamen():
    # Deterministic random-sequential-adsorption analogue: thousands of
    # 2--8 px asymmetric locules are admitted only when they do not overlap.
    # Contact membranes and fibres descend from the accepted packing.  This
    # replaces three macro polar ellipses and is the only RSA process in W4.
    candidates = _sites(14000, 79, margin=-3.0)
    bucket_size = 10.0
    buckets = {}
    accepted = []
    radii = []
    for i, p in enumerate(candidates):
        p = np.asarray((np.clip(p[0], -2, S + 1),
                        np.clip(p[1], -2, S + 1)), np.float32)
        radius = 2.6 + ((i * 17 + i // 9) % 5) * .68
        bx, by = int(np.floor(p[0] / bucket_size)), int(np.floor(p[1] / bucket_size))
        clear = True
        for yy in range(by - 2, by + 3):
            for xx in range(bx - 2, bx + 3):
                for j in buckets.get((xx, yy), ()):
                    if np.linalg.norm(p - accepted[j]) < radius + radii[j] + .8:
                        clear = False
                        break
                if not clear:
                    break
            if not clear:
                break
        if not clear:
            continue
        accepted.append(p)
        radii.append(radius)
        buckets.setdefault((bx, by), []).append(len(accepted) - 1)
        if len(accepted) >= 2650:
            break
    outer_faces, inner_faces, membranes, septa = (_blank() for _ in range(4))
    fibres, pleats, pores, dehiscence, channels = (_blank() for _ in range(5))
    occupancy = np.zeros((S, S), np.uint8)
    for i, (p, radius) in enumerate(zip(accepted, radii)):
        centre = tuple(np.rint(p).astype(int))
        angle = (i * 137.507764 + 23.0 * np.sin(i * .37)) % 180.0
        axes = (max(2, int(round(radius + .7 * np.sin(i * 1.13)))),
                max(2, int(round(radius * (.62 + .12 * ((i * 7) % 3))))))
        target = outer_faces if ((i * 19 + i // 7) % 11) < 5 else inner_faces
        cv2.ellipse(target, centre, axes, angle, 0, 360,
                    .72 + .06 * (i % 5), -1, cv2.LINE_AA)
        cv2.ellipse(occupancy, centre, axes, angle, 0, 360, 255, -1,
                    cv2.LINE_AA)
        if i % 2 == 0:
            direction = np.asarray((np.cos(np.radians(angle)),
                                    np.sin(np.radians(angle))), np.float32)
            _line(fibres, p - direction * max(2, axes[0] - 1),
                  p + direction * max(2, axes[0] - 1), 2)
        if i % 13 == 0:
            _circle(pores, p, 2, 2)
        if i % 17 == 0:
            d = np.asarray((np.cos(np.radians(angle + 73)),
                            np.sin(np.radians(angle + 73))), np.float32)
            _line(dehiscence, p - d * 3, p + d * 4, 2)
    membrane_base = _edge((occupancy > 0).astype(np.float32), 1)
    membranes[:] = membrane_base
    # Narrow voids between accepted locules are genuine contact septa.
    septa[:] = _f(_dilate((occupancy > 0).astype(np.float32), 2)
                  - (occupancy > 0).astype(np.float32))
    pleats[:] = _edge(np.maximum(inner_faces, membranes), 1)
    # Contact channels join only nearby accepted neighbours.
    accepted_arr = np.asarray(accepted, np.float32)
    for i in range(0, len(accepted), 19):
        d2 = np.sum((accepted_arr - accepted_arr[i]) ** 2, axis=1)
        for j in np.argsort(d2)[1:4]:
            if d2[j] <= 14.0 ** 2:
                _line(channels, accepted_arr[i], accepted_arr[int(j)], 2)
                break
    masks = dict(mature_locule_faces=outer_faces,
                 translucent_locule_faces=inner_faces,
                 contact_membranes=membranes, unequal_contact_septa=septa,
                 internal_locule_fibres=fibres, vascular_pleats=pleats,
                 locule_pores=pores, dehiscence_paths=dehiscence,
                 short_pollen_channels=channels)
    banks = dict(mature_locule_faces="A", translucent_locule_faces="B",
                 contact_membranes="A", unequal_contact_septa="N",
                 internal_locule_fibres="B", vascular_pleats="A",
                 locule_pores="N", dehiscence_paths="B",
                 short_pollen_channels="B")
    spec = _literal_spec(
        masks,
        (("mature_locule_faces", 238), ("contact_membranes", 252),
         ("vascular_pleats", 208), ("unequal_contact_septa", 134),
         ("locule_pores", 104), ("translucent_locule_faces", 20),
         ("internal_locule_fibres", 48), ("dehiscence_paths", 76),
         ("short_pollen_channels", 94)),
        (("mature_locule_faces", 52), ("contact_membranes", 24),
         ("vascular_pleats", 78), ("unequal_contact_septa", 156),
         ("locule_pores", 204), ("translucent_locule_faces", 228),
         ("internal_locule_fibres", 188), ("dehiscence_paths", 142),
         ("short_pollen_channels", 106)),
        (("mature_locule_faces", 22), ("contact_membranes", 10),
         ("vascular_pleats", 52), ("unequal_contact_septa", 126),
         ("locule_pores", 112), ("translucent_locule_faces", 252),
         ("internal_locule_fibres", 226), ("dehiscence_paths", 198),
         ("short_pollen_channels", 174)))
    local_depth = cv2.distanceTransform((occupancy > 0).astype(np.uint8),
                                        cv2.DIST_L2, 5)
    return _finish(masks, banks, _n(local_depth) + .33 * outer_faces
                   + .71 * inner_faces, spec)


# 13 — crop-to-crop Delaunay orchid marquetry with no rectangular hull.
def w4_magenta_mosaic():
    # Delaunay is retained only for this ID, but the rejected 196-site inner
    # rectangle is gone.  Dense sites plus an explicit off-crop perimeter make
    # 2--8 px facets terminate naturally on all four crop edges.
    interior = _sites(2700, 97, margin=-34)
    perimeter = []
    for v in range(-32, S + 33, 8):
        perimeter.extend(((-36, v), (S + 35, v),
                          (v, -36), (v, S + 35)))
    sites = np.vstack((interior, np.asarray(perimeter, np.float32)))
    subdiv = cv2.Subdiv2D((-40, -40, S + 80, S + 80))
    for x, y in sites:
        subdiv.insert((float(x), float(y)))
    triangles = subdiv.getTriangleList()
    facet_a, facet_b, grout, veins = (_blank() for _ in range(4))
    lips, tears, punctures, scars, folds = (_blank() for _ in range(5))
    kept = 0
    for tri in triangles:
        pts = np.asarray(tri, np.float32).reshape(3, 2)
        center = pts.mean(axis=0)
        if not (-18 <= center[0] <= S + 18 and -18 <= center[1] <= S + 18):
            continue
        area = abs(np.cross(pts[1] - pts[0], pts[2] - pts[0])) * .5
        if area < 7 or area > 620:
            continue
        lengths = np.linalg.norm(pts - np.roll(pts, -1, axis=0), axis=1)
        signature = int(round(area * 3.1 + lengths.max() * 11.7
                              + lengths.min() * 17.3
                              + center[0] * .37 + center[1] * .19))
        target = facet_a if signature % 11 < 5 else facet_b
        _poly(target, pts, fill=True, value=.68 + .055 * (signature % 5))
        _poly(grout, pts, width=1)
        mids = .5 * (pts + np.roll(pts, -1, axis=0))
        if signature % 3:
            _line(veins, center, mids[signature % 3], 2)
        if signature % 7 == 0:
            _line(veins, center, mids[(signature + 1) % 3], 2)
        if signature % 13 == 0:
            _line(tears, center - (4, 3), center + (7, -5), 2)
        if signature % 19 == 0:
            _circle(punctures, center, 2, 2)
        kept += 1
    lips[:] = _edge(grout, 1)
    scars[:] = _halo(np.maximum(tears, punctures), 1.1)
    folds[:] = _edge(np.maximum(facet_a, facet_b), 1)
    masks = dict(mature_orchid_facets=facet_a, young_orchid_facets=facet_b,
                 neutral_resin_grout=grout, facet_internal_veins=veins,
                 folded_facet_lips=lips, tissue_tears=tears,
                 facet_punctures=punctures, healed_scars=scars,
                 facet_fold_edges=folds)
    banks = dict(mature_orchid_facets="A", young_orchid_facets="B",
                 neutral_resin_grout="N", facet_internal_veins="A",
                 folded_facet_lips="B", tissue_tears="B",
                 facet_punctures="N", healed_scars="A", facet_fold_edges="B")
    spec = _literal_spec(
        masks,
        (("mature_orchid_facets", 242), ("facet_internal_veins", 214),
         ("healed_scars", 176), ("neutral_resin_grout", 126),
         ("facet_punctures", 102), ("young_orchid_facets", 22),
         ("folded_facet_lips", 54), ("tissue_tears", 78),
         ("facet_fold_edges", 92)),
        (("mature_orchid_facets", 38), ("facet_internal_veins", 72),
         ("healed_scars", 116), ("neutral_resin_grout", 162),
         ("facet_punctures", 206), ("young_orchid_facets", 224),
         ("folded_facet_lips", 88), ("tissue_tears", 142),
         ("facet_fold_edges", 182)),
        (("mature_orchid_facets", 16), ("facet_internal_veins", 46),
         ("healed_scars", 82), ("neutral_resin_grout", 136),
         ("facet_punctures", 112), ("young_orchid_facets", 252),
         ("folded_facet_lips", 222), ("tissue_tears", 188),
         ("facet_fold_edges", 204)))
    return _finish(masks, banks, _distance_to_ink(grout)
                   + .31 * facet_a + .69 * facet_b, spec)


# 14 — fused rhizome continent with locally differentiated organs.
def w4_leaf_whorl():
    # Auxin canalisation: distributed boundary sources route toward unequal
    # sinks while blurred conductance attracts later growth into local
    # inosculations.  Six hard-coded decorated trunks are no longer present.
    rhizome, cambium, grafts, blade_tissue = (_blank() for _ in range(4))
    pitcher_folds, crozier_tips, tendrils, pores, scars = (_blank() for _ in range(5))
    mature_sheet, young_sheet = _blank(), _blank()
    conductance = _blank()

    def boundary_point(index, side):
        q = 8.0 + ((index * 47.0 + 19.0 * np.sin(index * 1.17 + side))
                   % (S - 16.0))
        if side == 0:
            return np.asarray((2.0, q), np.float32)
        if side == 1:
            return np.asarray((S - 3.0, q), np.float32)
        if side == 2:
            return np.asarray((q, 2.0), np.float32)
        return np.asarray((q, S - 3.0), np.float32)

    grad_x = grad_y = np.zeros_like(conductance)
    for route in range(132):
        if route % 4 == 0:
            blurred = cv2.GaussianBlur(conductance, (0, 0), 3.2)
            grad_x = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
        source_side = route % 4
        target_side = (route * 3 + 1 + route // 11) % 4
        if target_side == source_side:
            target_side = (target_side + 1) % 4
        p = boundary_point(route, source_side)
        target = boundary_point(route * 5 + 17, target_side)
        route_pulse = _blank()
        for step in range(118):
            goal = target - p
            distance = np.linalg.norm(goal)
            if distance < 6.0:
                break
            goal /= distance + 1.0e-6
            ix, iy = int(np.clip(round(p[0]), 0, S - 1)), int(np.clip(round(p[1]), 0, S - 1))
            attraction = np.asarray((grad_x[iy, ix], grad_y[iy, ix]), np.float32)
            attraction /= np.linalg.norm(attraction) + 1.0e-6
            field_angle = (.43 * np.sin(p[1] / 57.0 + route * .19)
                           - .37 * np.cos(p[0] / 71.0 - route * .13))
            field = np.asarray((np.cos(field_angle), np.sin(field_angle)), np.float32)
            direction = .67 * goal + .31 * field + .43 * attraction
            direction /= np.linalg.norm(direction) + 1.0e-6
            endpoint = p + direction * (4.1 + ((route * 7 + step) % 5) * .36)
            endpoint = np.clip(endpoint, 1.0, S - 2.0)
            existing = conductance[iy, ix]
            target_mask = rhizome if existing > .36 else cambium
            _line(target_mask, p, endpoint, 2 + (existing > .62))
            _line(route_pulse, p, endpoint, 2,
                  value=.12 + .025 * (route % 4))
            tangent = direction
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            if existing > .48 and step > 5:
                _circle(grafts, p, 2, width=-1)
            if (route * 13 + step) % 23 == 0:
                side = -1.0 if (route + step) % 2 else 1.0
                tip = p + side * normal * (4 + route % 6) + tangent * 2
                organ = (route + step) % 3
                if organ == 0:
                    _curve(blade_tissue, (p - tangent * 2, tip, p + tangent * 3), 2)
                elif organ == 1:
                    _curve(pitcher_folds, _open_arc(tip, 3, 4,
                                                   np.arctan2(normal[1], normal[0]),
                                                   2.9, 12), 2)
                else:
                    _curve(crozier_tips, _open_arc(tip, 3, 2,
                                                  np.arctan2(tangent[1], tangent[0]),
                                                  3.5, 12), 2)
                _line(tendrils, p, tip, 2)
            if (route * 7 + step) % 41 == 0:
                _circle(pores, p, 2, 2)
            p = endpoint
        # Route-level accumulation preserves the causal canalisation field
        # while avoiding a full 512-square array add at every micro-step.
        conductance[:] = _f(conductance + route_pulse)
    mature_sheet[:] = _f((conductance - .38) / .22 + .5)
    channel_union = _dilate(np.maximum(rhizome, cambium), 3)
    young_sheet[:] = _f(channel_union - .72 * mature_sheet)
    scars[:] = _edge(np.maximum(mature_sheet, grafts), 1)
    masks = dict(rhizome_core=rhizome, cambium_channels=cambium,
                 mature_canalised_tissue=mature_sheet,
                 young_canalised_tissue=young_sheet,
                 regrafting_bridges=grafts, local_blade_tissue=blade_tissue,
                 local_pitcher_folds=pitcher_folds, crozier_growth_tips=crozier_tips,
                 shared_tendril_tissue=tendrils, rhizome_pores=pores,
                 healed_graft_scars=scars)
    banks = dict(rhizome_core="A", cambium_channels="A",
                 mature_canalised_tissue="A", young_canalised_tissue="B",
                 regrafting_bridges="N", local_blade_tissue="B",
                 local_pitcher_folds="B", crozier_growth_tips="B",
                 shared_tendril_tissue="B", rhizome_pores="N",
                 healed_graft_scars="A")
    spec = _literal_spec(
        masks,
        (("mature_canalised_tissue", 236), ("rhizome_core", 252),
         ("cambium_channels", 220),
         ("healed_graft_scars", 182), ("regrafting_bridges", 128),
         ("rhizome_pores", 96), ("young_canalised_tissue", 20),
         ("local_blade_tissue", 46),
         ("local_pitcher_folds", 48), ("crozier_growth_tips", 76),
         ("shared_tendril_tissue", 90)),
        (("mature_canalised_tissue", 54), ("rhizome_core", 26),
         ("cambium_channels", 68),
         ("healed_graft_scars", 108), ("regrafting_bridges", 158),
         ("rhizome_pores", 206), ("young_canalised_tissue", 228),
         ("local_blade_tissue", 196),
         ("local_pitcher_folds", 88), ("crozier_growth_tips", 138),
         ("shared_tendril_tissue", 184)),
        (("mature_canalised_tissue", 22), ("rhizome_core", 10),
         ("cambium_channels", 42),
         ("healed_graft_scars", 78), ("regrafting_bridges", 132),
         ("rhizome_pores", 112), ("young_canalised_tissue", 252),
         ("local_blade_tissue", 232),
         ("local_pitcher_folds", 224), ("crozier_growth_tips", 190),
         ("shared_tendril_tissue", 208)))
    return _finish(masks, banks, conductance + .31 * mature_sheet
                   + .69 * young_sheet, spec)


# 15 — directed wind-shear rupture graph with local tributaries.
def w4_white_pollen():
    # Anisotropic phase-fracture sheet under spatially varying shear.  Damage
    # propagates from unequal boundary notches only through locally admissible
    # toughness, replacing eight parallel hand-scripted wind lanes.
    wx = X + 13.0 * np.sin(Y / 73.0) - 5.0 * np.sin((X - Y) / 109.0)
    wy = Y + 10.0 * np.sin(X / 61.0 + .8) + 4.0 * np.sin((2 * X + Y) / 127.0)
    theta = (1.17 * np.sin(wx / 83.0) - .91 * np.cos(wy / 67.0)
             + .43 * np.sin((wx + wy) / 47.0))
    drive = _n(np.abs(np.sin(.191 * wx + .117 * wy)
                      + .73 * np.sin(.083 * wx - .247 * wy + .6)
                      + .41 * np.cos(.311 * wy + .071 * wx)))
    toughness = _n(np.abs(np.cos(.137 * wx - .099 * wy)
                          + .52 * np.sin(.223 * wx + .181 * wy)))
    eligible = drive > (.43 + .11 * toughness)
    reached = _blank()
    for i in range(14):
        q = int(12 + (i * 73 + 19 * np.sin(i * 1.37)) % (S - 24))
        side = i % 4
        if side == 0:
            _line(reached, (0, q), (5 + i % 4, q + i % 5 - 2), 2)
        elif side == 1:
            _line(reached, (S - 1, q), (S - 7 - i % 4, q - i % 5 + 2), 2)
        elif side == 2:
            _line(reached, (q, 0), (q + i % 5 - 2, 5 + i % 4), 2)
        else:
            _line(reached, (q, S - 1), (q - i % 5 + 2, S - 7 - i % 4), 2)
    directions = ((-1, -1), (0, -1), (1, -1), (-1, 0),
                  (1, 0), (-1, 1), (0, 1), (1, 1))
    for _iteration in range(118):
        propagated = np.zeros_like(reached)
        for dx, dy in directions:
            shifted = np.zeros_like(reached)
            ys = slice(max(0, dy), min(S, S + dy))
            xs = slice(max(0, dx), min(S, S + dx))
            source_y = slice(max(0, -dy), min(S, S - dy))
            source_x = slice(max(0, -dx), min(S, S - dx))
            shifted[ys, xs] = reached[source_y, source_x]
            direction_angle = np.arctan2(dy, dx)
            alignment = .70 + .30 * np.abs(np.cos(theta - direction_angle))
            propagated = np.maximum(propagated, shifted * alignment)
        new_reached = np.maximum(reached,
                                 eligible.astype(np.float32)
                                 * _f((propagated - .19) / .64 + .31))
        if float(np.max(np.abs(new_reached - reached))) < 1.0e-4:
            reached = new_reached
            break
        reached = new_reached
    crack = (reached > .38).astype(np.float32)
    trunks = crack * (drive > .72)
    tributaries = crack * (drive <= .72)
    intact = 1.0 - _dilate(crack, 1)
    shear_side = np.sin(theta + .37 * toughness)
    compressed = intact * np.where(shear_side >= 0,
                                   .72 + .24 * drive, 0.0).astype(np.float32)
    stretched = intact * np.where(shear_side < 0,
                                  .72 + .24 * (1.0 - toughness), 0.0).astype(np.float32)
    neighbours = cv2.filter2D(crack.astype(np.uint8), -1,
                              np.ones((3, 3), np.uint8))
    local_drive_max = drive >= (cv2.dilate(drive, np.ones((7, 7), np.uint8))
                                - 1.0e-6)
    pores = _dilate(((crack > 0) & (neighbours >= 5) & local_drive_max)
                    .astype(np.float32), 1)
    arrests = _dilate(((crack > 0) & (neighbours <= 2)).astype(np.float32), 1)
    folds = _halo(crack, 1.2)
    lips = _edge(_dilate(crack, 1), 1)
    microsepta = _edge(compressed, 1) * _edge(stretched, 1)
    masks = dict(upwind_rupture_trunks=trunks, branching_tributaries=tributaries,
                 compressed_membrane=compressed, stretched_lee_membrane=stretched,
                 junction_pore_chains=pores, local_fold_webs=folds,
                 rupture_lips=lips, arrested_crack_tips=arrests,
                 micro_septa=microsepta)
    banks = dict(upwind_rupture_trunks="A", branching_tributaries="B",
                 compressed_membrane="A", stretched_lee_membrane="B",
                 junction_pore_chains="N", local_fold_webs="A",
                 rupture_lips="B", arrested_crack_tips="N", micro_septa="B")
    spec = _literal_spec(
        masks,
        (("upwind_rupture_trunks", 248), ("compressed_membrane", 216),
         ("local_fold_webs", 178), ("arrested_crack_tips", 124),
         ("junction_pore_chains", 98), ("branching_tributaries", 18),
         ("stretched_lee_membrane", 46), ("rupture_lips", 74),
         ("micro_septa", 88)),
        (("upwind_rupture_trunks", 40), ("compressed_membrane", 76),
         ("local_fold_webs", 116), ("arrested_crack_tips", 162),
         ("junction_pore_chains", 208), ("branching_tributaries", 224),
         ("stretched_lee_membrane", 92), ("rupture_lips", 142),
         ("micro_septa", 182)),
        (("upwind_rupture_trunks", 16), ("compressed_membrane", 48),
         ("local_fold_webs", 82), ("arrested_crack_tips", 118),
         ("junction_pore_chains", 136), ("branching_tributaries", 252),
         ("stretched_lee_membrane", 226), ("rupture_lips", 190),
         ("micro_septa", 208)))
    return _finish(masks, banks, drive + .31 * compressed
                   + .69 * stretched - .17 * toughness, spec)


# 16 — irregular continuous stamen organ cropped through multiple edges.
def w4_pink_stamen():
    # Kinetic micro-locule collision tissue.  Hundreds of asymmetric locules
    # move, reflect, collide and leave short connective histories.  The former
    # single spine and thirteen repeated diamonds are completely absent.
    count = 760
    positions = _sites(count, 113, margin=7.0)
    indices = np.arange(count, dtype=np.float32)
    angles = indices * 2.399963 + .41 * np.sin(indices * .71)
    speeds = 1.35 + ((indices.astype(np.int32) * 17) % 7) * .17
    velocities = np.c_[np.cos(angles) * speeds,
                       np.sin(angles) * speeds].astype(np.float32)
    radii = 3.0 + ((indices.astype(np.int32) * 11
                    + indices.astype(np.int32) // 9) % 5).astype(np.float32)
    connective, filament_core, dehiscence = (_blank() for _ in range(3))
    channels, pleats, pores, scars, side_fibres = (_blank() for _ in range(5))
    collision_count = np.zeros(count, np.int16)
    for step in range(30):
        previous = positions.copy()
        positions += velocities
        for axis in (0, 1):
            low = positions[:, axis] < 5
            high = positions[:, axis] > S - 6
            positions[low, axis] = 10 - positions[low, axis]
            positions[high, axis] = 2 * (S - 6) - positions[high, axis]
            velocities[low | high, axis] *= -1
        buckets = {}
        for i, p in enumerate(positions):
            key = (int(p[0] // 16), int(p[1] // 16))
            for yy in range(key[1] - 1, key[1] + 2):
                for xx in range(key[0] - 1, key[0] + 2):
                    for j in buckets.get((xx, yy), ()):
                        delta = p - positions[j]
                        distance = np.linalg.norm(delta)
                        threshold = radii[i] + radii[j] + .7
                        if distance >= threshold or distance < 1.0e-5:
                            continue
                        normal = delta / distance
                        vi = float(np.dot(velocities[i], normal))
                        vj = float(np.dot(velocities[j], normal))
                        velocities[i] += (vj - vi) * normal
                        velocities[j] += (vi - vj) * normal
                        collision_count[i] += 1
                        collision_count[j] += 1
                        if (i * 17 + j * 7 + step) % 5 == 0:
                            _line(connective, p, positions[j], 2)
                            midpoint = .5 * (p + positions[j])
                            _circle(scars, midpoint, 2, 2)
                        if (i + j + step) % 19 == 0:
                            _circle(pores, .5 * (p + positions[j]), 2, 2)
            buckets.setdefault(key, []).append(i)
        for i in range(step % 3, count, 3):
            target = filament_core if (i + step) % 2 else channels
            _line(target, previous[i], positions[i], 2)
    mature_faces, young_faces, locule_membrane = (_blank() for _ in range(3))
    for i, (p, radius) in enumerate(zip(positions, radii)):
        velocity = velocities[i]
        angle = float(np.degrees(np.arctan2(velocity[1], velocity[0])))
        axes = (max(2, int(round(radius))),
                max(2, int(round(radius * (.57 + .07 * (i % 4))))))
        target = mature_faces if ((i * 23 + collision_count[i]) % 11) < 5 else young_faces
        cv2.ellipse(target, tuple(np.rint(p).astype(int)), axes, angle,
                    0, 360, .70 + .055 * (i % 5), -1, cv2.LINE_AA)
        if collision_count[i] >= 3:
            d = velocity / (np.linalg.norm(velocity) + 1.0e-6)
            n = np.asarray((-d[1], d[0]), np.float32)
            _line(dehiscence, p - n * 3, p + n * 4, 2)
            if i % 3 == 0:
                _line(side_fibres, p, p + d * 4 + n * 4, 2)
    locule_membrane[:] = _edge(np.maximum(mature_faces, young_faces), 1)
    pleats[:] = _edge(_dilate(connective, 2), 1)
    scars[:] = np.maximum(scars, _edge(np.maximum(locule_membrane, dehiscence), 1))
    masks = dict(mature_collision_locules=mature_faces,
                 young_collision_locules=young_faces,
                 collision_connective=connective,
                 filament_history_core=filament_core,
                 irregular_locule_membranes=locule_membrane,
                 dehiscence_lips=dehiscence, pollen_channels=channels,
                 connective_pleats=pleats, locule_pores=pores,
                 healed_attachment_scars=scars, side_fibre_sprays=side_fibres)
    banks = dict(mature_collision_locules="A", young_collision_locules="B",
                 collision_connective="A", filament_history_core="A",
                 irregular_locule_membranes="B", dehiscence_lips="B",
                 pollen_channels="B", connective_pleats="N",
                 locule_pores="N", healed_attachment_scars="A",
                 side_fibre_sprays="B")
    spec = _literal_spec(
        masks,
        (("mature_collision_locules", 238), ("collision_connective", 252),
         ("filament_history_core", 216),
         ("healed_attachment_scars", 176), ("connective_pleats", 126),
         ("locule_pores", 98), ("young_collision_locules", 20),
         ("irregular_locule_membranes", 48),
         ("dehiscence_lips", 48), ("pollen_channels", 76),
         ("side_fibre_sprays", 90)),
        (("mature_collision_locules", 52), ("collision_connective", 24),
         ("filament_history_core", 74),
         ("healed_attachment_scars", 112), ("connective_pleats", 158),
         ("locule_pores", 204), ("young_collision_locules", 228),
         ("irregular_locule_membranes", 196),
         ("dehiscence_lips", 88), ("pollen_channels", 138),
         ("side_fibre_sprays", 184)),
        (("mature_collision_locules", 22), ("collision_connective", 10),
         ("filament_history_core", 48),
         ("healed_attachment_scars", 82), ("connective_pleats", 134),
         ("locule_pores", 116), ("young_collision_locules", 252),
         ("irregular_locule_membranes", 224),
         ("dehiscence_lips", 224), ("pollen_channels", 188),
         ("side_fibre_sprays", 206)))
    collision_field = np.zeros((S, S), np.float32)
    for p, count_i in zip(positions, collision_count):
        if count_i:
            _circle(collision_field, p, 2 + min(4, int(count_i // 2)),
                    value=min(1.0, .16 * count_i), width=-1)
    return _finish(masks, banks, _n(collision_field)
                   + .31 * mature_faces + .69 * young_faces, spec)


# 17 — curve-source front collisions; distinct from point-cell exine foam.
def w4_blush_rose():
    # Dense curve-source collision sheet.  The first board used twelve macro
    # fronts that converged at one obvious hub; 2,300 oriented microfronts now
    # occupy the whole domain and are solved in one labelled distance pass.
    centres = _sites(2300, 101, margin=-3.0)
    seed = np.ones((S, S), np.uint8)
    source_at_seed = np.full((S, S), -1, np.int32)
    ribs, tears, scars, pores, tributaries = (_blank() for _ in range(5))
    for i, p in enumerate(centres):
        angle = i * 2.399963 + .47 * np.sin(p[0] / 37.0 - p[1] / 43.0)
        direction = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
        normal = np.asarray((-direction[1], direction[0]), np.float32)
        length = 3.0 + ((i * 13 + i // 11) % 7)
        start = p - direction * length * .45
        end = p + direction * length * .55 + normal * (1 + i % 3)
        path = _bezier(start, start + direction * length * .3 + normal * 2,
                       start + direction * length * .72 - normal * 2, end, 10)
        pts = np.rint(path).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(seed, [pts], False, 0, 1, cv2.LINE_8)
        cv2.polylines(source_at_seed, [pts], False, int(i), 2, cv2.LINE_8)
        _curve(ribs if i % 2 else tributaries, path, 2)
        if i % 29 == 0:
            _line(tears, p - normal * 3, p + normal * 4, 2)
        if i % 37 == 0:
            _circle(pores, p, 2, 2)
    raw_depth, pixel_label = cv2.distanceTransformWithLabels(
        seed, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    mapping = np.zeros(int(pixel_label.max()) + 1, np.int32)
    zero = seed == 0
    mapping[pixel_label[zero]] = np.maximum(source_at_seed[zero], 0)
    label = mapping[pixel_label]
    depth = _n(raw_depth)
    boundaries = _cell_edges(label, 1)
    lineage = (label * 43 + label // 17 * 19) % 23
    compressed = np.where(lineage < 11,
                          .72 + .05 * (lineage % 5), 0.0).astype(np.float32)
    relaxed = np.where(lineage >= 11,
                       .70 + .045 * ((lineage + 3) % 6), 0.0).astype(np.float32)
    folds = _f(_dilate(boundaries, 3) - _dilate(boundaries, 1))
    lips = _edge(boundaries, 1)
    scars[:] = _halo(np.maximum(tears, boundaries), 1.05)
    masks = dict(compressed_collision_tissue=compressed,
                 relaxed_translucent_tissue=relaxed,
                 interlocking_collision_boundaries=boundaries,
                 local_fold_webs=folds, folded_collision_lips=lips,
                 rib_tributaries=ribs, tissue_tears=tears,
                 healed_scars=scars, cuticle_pores=pores,
                 vascular_tributaries=tributaries)
    banks = dict(compressed_collision_tissue="A",
                 relaxed_translucent_tissue="B",
                 interlocking_collision_boundaries="N", local_fold_webs="A",
                 folded_collision_lips="B", rib_tributaries="A",
                 tissue_tears="B", healed_scars="N", cuticle_pores="B",
                 vascular_tributaries="A")
    spec = _literal_spec(
        masks,
        (("compressed_collision_tissue", 244), ("local_fold_webs", 214),
         ("rib_tributaries", 182), ("vascular_tributaries", 156),
         ("interlocking_collision_boundaries", 126), ("healed_scars", 102),
         ("relaxed_translucent_tissue", 18), ("folded_collision_lips", 52),
         ("tissue_tears", 76), ("cuticle_pores", 90)),
        (("compressed_collision_tissue", 40), ("local_fold_webs", 74),
         ("rib_tributaries", 108), ("vascular_tributaries", 142),
         ("interlocking_collision_boundaries", 176), ("healed_scars", 206),
         ("relaxed_translucent_tissue", 224), ("folded_collision_lips", 88),
         ("tissue_tears", 158), ("cuticle_pores", 118)),
        (("compressed_collision_tissue", 16), ("local_fold_webs", 44),
         ("rib_tributaries", 78), ("vascular_tributaries", 104),
         ("interlocking_collision_boundaries", 136), ("healed_scars", 116),
         ("relaxed_translucent_tissue", 252), ("folded_collision_lips", 224),
         ("tissue_tears", 190), ("cuticle_pores", 206)))
    tone = ((label * 31 + label // 13 * 7) % 97).astype(np.float32) / 96.0
    return _finish(masks, banks, tone + .19 * depth + .11 * folds, spec)


# 18 — fused canopy with unequal pendants and lateral graft chronology.
def w4_lilac_vine():
    # Deterministic self-avoiding boundary bridges on one irregular support
    # graph.  Dynamic node penalties spread the bridge ensemble in every
    # direction, replacing the old horizontal canopy plus vertical pendant grid.
    canopy, pendants, grafts, cambium = (_blank() for _ in range(4))
    leaf_ribs, racemes, tendrils, nodes_mask, scars = (_blank() for _ in range(5))
    mature_sheet, young_sheet = _blank(), _blank()
    boundary = []
    side_indices = [[] for _ in range(4)]
    for i in range(7):
        q = 24.0 + i * 77.0 + 8.0 * np.sin(i * 1.51)
        for side, point in enumerate(((-4, q), (S + 3, (q * 1.23 + 49) % S),
                                      ((q * .79 + 83) % S, -4),
                                      ((q * 1.09 + 31) % S, S + 3))):
            side_indices[side].append(len(boundary))
            boundary.append(point)
    points = np.vstack((np.asarray(boundary, np.float32),
                        _sites(760, 127, margin=4.0)))
    delta = points[:, None, :] - points[None, :, :]
    d2 = np.sum(delta * delta, axis=2)
    np.fill_diagonal(d2, np.inf)
    neighbour_ids = np.argpartition(d2, 8, axis=1)[:, :8]
    adjacency = []
    for i, row in enumerate(neighbour_ids):
        adjacency.append([(int(j), float(np.sqrt(d2[i, j]))) for j in row])
    pairs = []
    for i in range(7):
        pairs.extend(((side_indices[0][i], side_indices[3][(i * 3 + 2) % 7]),
                      (side_indices[1][i], side_indices[2][(i * 5 + 1) % 7]),
                      (side_indices[0][i], side_indices[1][(i * 2 + 3) % 7])))
    usage = np.zeros(len(points), np.float32)
    paths = []
    for path_i, (source, target) in enumerate(pairs):
        distance = np.full(len(points), np.inf, np.float64)
        previous = np.full(len(points), -1, np.int32)
        distance[source] = 0.0
        queue = [(0.0, int(source))]
        while queue:
            cost, node = heapq.heappop(queue)
            if cost != distance[node]:
                continue
            if node == target:
                break
            for other, length in adjacency[node]:
                penalty = 1.0 + 2.8 * usage[other] + .65 * usage[node]
                candidate = cost + length * penalty
                if candidate < distance[other]:
                    distance[other] = candidate
                    previous[other] = node
                    heapq.heappush(queue, (candidate, other))
        if previous[target] < 0:
            continue
        path_nodes = [int(target)]
        while path_nodes[-1] != source:
            path_nodes.append(int(previous[path_nodes[-1]]))
        path_nodes.reverse()
        usage[path_nodes] += 1.0
        path = points[path_nodes]
        paths.append(path)
        target_mask = canopy if path_i % 3 == 0 else (
            cambium if path_i % 3 == 1 else pendants)
        _curve(target_mask, path, 2 + (path_i % 4 == 0))
        for q in range(2 + path_i % 3, len(path) - 2, 5 + path_i % 4):
            p = path[q]
            tangent = path[q + 1] - path[q - 1]
            tangent /= np.linalg.norm(tangent) + 1.0e-6
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            side = -1.0 if (path_i + q) % 2 else 1.0
            _line(leaf_ribs, p, p + side * normal * (5 + q % 6), 2)
            if (path_i + q) % 3 == 0:
                _curve(tendrils, _open_arc(p + side * normal * 4, 3, 2,
                                          path_i * .37 + q, 3.3, 12), 2)
            if (path_i + q) % 5 == 0:
                tip = p - side * normal * (5 + path_i % 4) + tangent * 3
                _line(racemes, p, tip, 2)
    for p, visits in zip(points, usage):
        if visits >= 2:
            _circle(grafts, p, 2 + min(3, int(visits) - 2), width=-1)
    nodes_mask[:] = _edge(grafts, 1)
    mature_sheet[:] = _f(.88 * _dilate(np.maximum(canopy, cambium), 4)
                          + .62 * grafts)
    young_sheet[:] = _f(.88 * _dilate(pendants, 4)
                         + .58 * _dilate(np.maximum(leaf_ribs, racemes), 2))
    scars[:] = _edge(np.maximum(mature_sheet, grafts), 1)
    masks = dict(overhead_lignified_canopy=canopy, young_pendant_tissue=pendants,
                 mature_bridge_sheet=mature_sheet, young_bridge_sheet=young_sheet,
                 lateral_depth_grafts=grafts, pendant_cambium=cambium,
                 leaf_ribs=leaf_ribs, raceme_channels=racemes,
                 tendril_coils=tendrils, graft_nodes=nodes_mask,
                 canopy_scars=scars)
    banks = dict(overhead_lignified_canopy="A", young_pendant_tissue="B",
                 mature_bridge_sheet="A", young_bridge_sheet="B",
                 lateral_depth_grafts="A", pendant_cambium="A",
                 leaf_ribs="B", raceme_channels="B", tendril_coils="B",
                 graft_nodes="N", canopy_scars="A")
    spec = _literal_spec(
        masks,
        (("mature_bridge_sheet", 236), ("overhead_lignified_canopy", 252),
         ("lateral_depth_grafts", 220),
         ("pendant_cambium", 184), ("canopy_scars", 154),
         ("graft_nodes", 116), ("young_bridge_sheet", 20),
         ("young_pendant_tissue", 46),
         ("leaf_ribs", 46), ("raceme_channels", 72), ("tendril_coils", 88)),
        (("mature_bridge_sheet", 54), ("overhead_lignified_canopy", 26),
         ("lateral_depth_grafts", 68),
         ("pendant_cambium", 104), ("canopy_scars", 146),
         ("graft_nodes", 202), ("young_bridge_sheet", 228),
         ("young_pendant_tissue", 198),
         ("leaf_ribs", 86), ("raceme_channels", 138), ("tendril_coils", 182)),
        (("mature_bridge_sheet", 22), ("overhead_lignified_canopy", 10),
         ("lateral_depth_grafts", 42),
         ("pendant_cambium", 76), ("canopy_scars", 108),
         ("graft_nodes", 132), ("young_bridge_sheet", 252),
         ("young_pendant_tissue", 232),
         ("leaf_ribs", 226), ("raceme_channels", 190), ("tendril_coils", 208)))
    return _finish(masks, banks,
                   _distance_to_ink(np.maximum(mature_sheet, young_sheet))
                   + .31 * mature_sheet + .69 * young_sheet, spec)


# 19 — oblique phyllotactic tissue raft of many fine cropped axes.
def w4_butter_whorl():
    # Several off-crop domains belong to one quasiconformal phyllotactic map.
    # Only short Fibonacci-neighbour joins are drawn, so the old eleven long
    # diagonal axes and their repeated tabs cannot reappear.
    mature_axes, young_axes, mature_bracts, young_bracts = (_blank() for _ in range(4))
    sheaths, bridges, hooks, pores, scars, capillaries = (_blank() for _ in range(6))
    golden = np.pi * (3.0 - np.sqrt(5.0))
    domains = (
        (np.asarray((-138.0, 154.0), np.float32),
         np.asarray(((1.12, .31), (-.18, .86)), np.float32), .17),
        (np.asarray((648.0, 96.0), np.float32),
         np.asarray(((-.93, .28), (.22, 1.08)), np.float32), 1.41),
        (np.asarray((196.0, -166.0), np.float32),
         np.asarray(((.86, -.37), (.29, 1.04)), np.float32), 2.63),
        (np.asarray((406.0, 676.0), np.float32),
         np.asarray(((1.02, .24), (-.33, -.91)), np.float32), 3.74),
    )
    domain_points = []
    global_index = 0
    for domain_i, (centre, matrix, phase) in enumerate(domains):
        points = {}
        for n in range(18, 5200):
            radius = 10.8 * np.sqrt(float(n))
            angle = n * golden + phase
            base = np.asarray((radius * np.cos(angle), radius * np.sin(angle)),
                              np.float32)
            p = centre + matrix @ base
            p += np.asarray((4.5 * np.sin(p[1] / 43.0 + phase),
                             3.8 * np.sin(p[0] / 51.0 - phase)), np.float32)
            if not (-7 <= p[0] <= S + 6 and -7 <= p[1] <= S + 6):
                continue
            points[n] = p
            domain_points.append((domain_i, n, p))
            local = matrix @ np.asarray((-np.sin(angle), np.cos(angle)), np.float32)
            local /= np.linalg.norm(local) + 1.0e-6
            normal = np.asarray((-local[1], local[0]), np.float32)
            axes = (3 + (n + domain_i) % 4, 2 + (n * 3 + domain_i) % 3)
            target = mature_bracts if ((n * 17 + domain_i) % 9) < 4 else young_bracts
            cv2.ellipse(target, tuple(np.rint(p).astype(int)), axes,
                        float(np.degrees(np.arctan2(local[1], local[0]))),
                        18, 336, .70 + .06 * (n % 5), -1, cv2.LINE_AA)
            for predecessor, target_axis in ((n - 13, mature_axes),
                                              (n - 21, young_axes)):
                if predecessor not in points:
                    continue
                q = points[predecessor]
                if np.linalg.norm(q - p) <= 42.0:
                    midpoint = .5 * (p + q) + normal * (2 + n % 3)
                    _curve(target_axis, (q, midpoint, p), 2)
            if global_index % 17 == 0:
                _curve(hooks, _open_arc(p + normal * 2, 3 + n % 2, 2,
                                        angle, 3.2, 12), 2)
            if global_index % 23 == 0:
                _circle(pores, p, 2, 2)
            global_index += 1
        domain_points.append((domain_i, -1, np.asarray((np.nan, np.nan))))
    # Sparse joins between nearby different domains are true vascular grafts.
    finite = [(d, n, p) for d, n, p in domain_points if n >= 0]
    buckets = {}
    for i, (domain_i, _n, p) in enumerate(finite):
        key = (int(np.floor(p[0] / 12.0)), int(np.floor(p[1] / 12.0)))
        for yy in range(key[1] - 1, key[1] + 2):
            for xx in range(key[0] - 1, key[0] + 2):
                for j in buckets.get((xx, yy), ()):
                    other_domain, _on, q = finite[j]
                    if (other_domain != domain_i
                            and np.linalg.norm(q - p) < 9.0
                            and (i * 19 + j * 7) % 31 == 0):
                        _line(bridges, p, q, 2)
                        break
        buckets.setdefault(key, []).append(i)
    bracts = np.maximum(mature_bracts, young_bracts)
    sheaths[:] = _edge(bracts, 1)
    scars[:] = _edge(np.maximum(bridges, sheaths), 1)
    capillaries[:] = _halo(np.maximum(bracts, hooks), .95)
    masks = dict(mature_phyllotactic_axes=mature_axes, young_axes=young_axes,
                 mature_bract_faces=mature_bracts,
                 young_bract_faces=young_bracts, unequal_bracts=bracts,
                 axis_sheaths=sheaths,
                 cross_axis_vascular_bridges=bridges, bract_hooks=hooks,
                 axis_pores=pores, bridge_scars=scars,
                 bract_capillaries=capillaries)
    banks = dict(mature_phyllotactic_axes="A", young_axes="B",
                 mature_bract_faces="A", young_bract_faces="B",
                 unequal_bracts="N", axis_sheaths="A",
                 cross_axis_vascular_bridges="N", bract_hooks="B",
                 axis_pores="N", bridge_scars="A", bract_capillaries="B")
    spec = _literal_spec(
        masks,
        (("mature_bract_faces", 236), ("mature_phyllotactic_axes", 252),
         ("axis_sheaths", 216),
         ("bridge_scars", 178), ("cross_axis_vascular_bridges", 126),
         ("axis_pores", 98), ("unequal_bracts", 112),
         ("young_bract_faces", 20), ("young_axes", 44),
         ("bract_hooks", 74), ("bract_capillaries", 90)),
        (("mature_bract_faces", 54), ("mature_phyllotactic_axes", 26),
         ("axis_sheaths", 72),
         ("bridge_scars", 112), ("cross_axis_vascular_bridges", 162),
         ("axis_pores", 204), ("unequal_bracts", 142),
         ("young_bract_faces", 228), ("young_axes", 196),
         ("bract_hooks", 142), ("bract_capillaries", 184)),
        (("mature_bract_faces", 22), ("mature_phyllotactic_axes", 10),
         ("axis_sheaths", 46),
         ("bridge_scars", 82), ("cross_axis_vascular_bridges", 134),
         ("axis_pores", 116), ("unequal_bracts", 132),
         ("young_bract_faces", 252), ("young_axes", 232),
         ("bract_hooks", 188), ("bract_capillaries", 206)))
    return _finish(masks, banks, _distance_to_ink(bracts)
                   + .31 * mature_bracts + .69 * young_bracts, spec)


# 20 — asymmetric fissure/arbor membrane without a radial attractor.
def w4_magenta_pollen():
    primary, secondary, membrane_a, membrane_b = (_blank() for _ in range(4))
    pores, bridges, lips, shards, arrests = (_blank() for _ in range(5))
    trunks = (
        _bezier((-24, 74), (118, 34), (306, 282), (534, 194)),
        _bezier((84, -24), (38, 212), (438, 334), (292, 536)),
        _bezier((536, 46), (362, 132), (196, 484), (-24, 386)),
        _bezier((-24, 492), (162, 338), (274, 86), (474, -24)),
        _bezier((456, 536), (382, 238), (88, 284), (204, -24)),
        _bezier((536, 410), (294, 482), (262, 94), (-24, 142)),
    )
    for j, path in enumerate(trunks):
        _curve(primary if j % 2 == 0 else membrane_a, path, 3)
        for k in range(8 + j, 123, 9 + j % 4):
            p = path[k]
            t = path[min(127, k + 2)] - path[max(0, k - 2)]
            t /= np.linalg.norm(t) + 1.0e-6
            n = np.asarray([-t[1], t[0]]) * (-1 if (j + k) % 2 else 1)
            end = p + n * (18 + (k * 7 + j * 11) % 35) + t * (6 + j)
            branch = _bezier(p, p + t * 5, p + n * 13, end, 27)
            _curve(secondary if (j + k) % 3 else membrane_b, branch, 2)
            if k % 3 == 0:
                _circle(pores, p, 2 + (j + k) % 2, 2)
                _line(arrests, end - t * 4, end + n * 5, 2)
            if k % 4 == 0:
                shard = (p + n * 4, p + n * 13 + t * 5,
                         p + n * 9 - t * 7)
                _curve(shards, shard, 2, closed=True)
    for a, b, ia, ib in ((0, 1, 62, 73), (1, 2, 89, 54), (2, 3, 76, 91),
                          (3, 4, 58, 82), (4, 5, 98, 69), (5, 0, 67, 94),
                          (0, 3, 84, 46), (2, 5, 97, 103)):
        _curve(bridges, _bezier(trunks[a][ia], trunks[a][ia] + (9, 12),
                                trunks[b][ib] + (-9, -12), trunks[b][ib], 26), 3)
    lips[:] = _edge(np.maximum(primary, secondary), 1)
    masks = dict(primary_fissure_arbor=primary, secondary_fissure_branches=secondary,
                 compressed_membrane_lineage=membrane_a,
                 stretched_membrane_lineage=membrane_b, germ_pores=pores,
                 inter_arbor_bridges=bridges, rupture_lips=lips,
                 internal_exine_shards=shards, arrested_fissure_tips=arrests)
    banks = dict(primary_fissure_arbor="A", secondary_fissure_branches="B",
                 compressed_membrane_lineage="A",
                 stretched_membrane_lineage="B", germ_pores="N",
                 inter_arbor_bridges="N", rupture_lips="A",
                 internal_exine_shards="B", arrested_fissure_tips="N")
    spec = _literal_spec(
        masks,
        (("primary_fissure_arbor", 250), ("compressed_membrane_lineage", 218),
         ("rupture_lips", 182), ("inter_arbor_bridges", 128),
         ("germ_pores", 98), ("arrested_fissure_tips", 112),
         ("secondary_fissure_branches", 18), ("stretched_membrane_lineage", 48),
         ("internal_exine_shards", 78)),
        (("primary_fissure_arbor", 34), ("compressed_membrane_lineage", 72),
         ("rupture_lips", 108), ("inter_arbor_bridges", 158),
         ("germ_pores", 204), ("arrested_fissure_tips", 126),
         ("secondary_fissure_branches", 226), ("stretched_membrane_lineage", 88),
         ("internal_exine_shards", 176)),
        (("primary_fissure_arbor", 14), ("compressed_membrane_lineage", 44),
         ("rupture_lips", 78), ("inter_arbor_bridges", 132),
         ("germ_pores", 116), ("arrested_fissure_tips", 102),
         ("secondary_fissure_branches", 252), ("stretched_membrane_lineage", 224),
         ("internal_exine_shards", 190)))
    return _finish(masks, banks, _distance_to_ink(np.maximum(primary, secondary))
                   + .18 * np.sin((X - 1.7 * Y) / 73.0), spec)


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fbl_magenta_whorl": w4_magenta_whorl,
    "fbl_leafvine_drape": w4_leafvine_drape,
    "fbl_butter_pollen": w4_butter_pollen,
    "fbl_pink_rose": w4_pink_rose,
    "fbl_coral_cluster": w4_coral_cluster,
    "fbl_butter_mosaic": w4_butter_mosaic,
    "fbl_pink_pollen": w4_pink_pollen,
    "fbl_white_whorl": w4_white_whorl,
    "fbl_coral_stamen": w4_coral_stamen,
    "fbl_lilac_rose": w4_lilac_rose,
    "fbl_coral_vine": w4_coral_vine,
    "fbl_lilac_stamen": w4_lilac_stamen,
    "fbl_magenta_mosaic": w4_magenta_mosaic,
    "fbl_leaf_whorl": w4_leaf_whorl,
    "fbl_white_pollen": w4_white_pollen,
    "fbl_pink_stamen": w4_pink_stamen,
    "fbl_blush_rose": w4_blush_rose,
    "fbl_lilac_vine": w4_lilac_vine,
    "fbl_butter_whorl": w4_butter_whorl,
    "fbl_magenta_pollen": w4_magenta_pollen,
}


if len(BUILDERS) != 20 or len({fn.__name__ for fn in BUILDERS.values()}) != 20:
    raise AssertionError("WR-B4 must own twenty distinct topology constructors")


__all__ = ["BUILDERS", "Grammar", "owner_unions"]
