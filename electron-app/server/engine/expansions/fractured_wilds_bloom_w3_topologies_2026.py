# -*- coding: utf-8 -*-
"""WR-B3 owner-eye rebuild topologies for the twenty Fractured Bloom IDs.

This module is intentionally art-only and unwired.  It replaces the rejected
single-emblem drawings with twenty deterministic, canvas-filling biological
constructions.  No RNG, sampled texture, grain, fleck field, common tile,
common hub, or shared decorative carrier is used.  Every returned mask is a
literal part of the named organism/material and is independently consumed by
paint and spec composition in the host candidate module.

Work resolution is 512 square.  Drawn primitives are 2--8 work pixels, which
is 8--32 pixels at the required 2048 output.  Broader territories are built
from connected fine anatomy rather than oversized standalone icons.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Mapping, Tuple

import cv2
import numpy as np


S = 512
Y, X = np.mgrid[0:S, 0:S].astype(np.float32)


@dataclass
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    tone: np.ndarray


def _f(a):
    return np.clip(np.asarray(a, np.float32), 0.0, 1.0)


def _n(a):
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return np.zeros_like(a) if hi - lo < 1.0e-7 else ((a - lo) / (hi - lo)).astype(np.float32)


def _edge(a, width=1):
    u = _f(a)
    k = np.ones((2 * int(width) + 1,) * 2, np.uint8)
    return _f(cv2.dilate(u, k) - cv2.erode(u, k))


def _halo(a, sigma=2.0):
    u = _f(a)
    return _f(cv2.GaussianBlur(u, (0, 0), float(sigma)) - 0.25 * u)


def _dilate(a, radius):
    k = np.ones((2 * int(radius) + 1,) * 2, np.uint8)
    return _f(cv2.dilate(_f(a), k))


def _erode(a, radius):
    k = np.ones((2 * int(radius) + 1,) * 2, np.uint8)
    return _f(cv2.erode(_f(a), k))


def _blank():
    return np.zeros((S, S), np.float32)


def _curve(mask, points, width=2, value=1.0, closed=False):
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    cv2.polylines(mask, [pts], bool(closed), float(value), int(width), cv2.LINE_AA)


def _circle(mask, center, radius, width=2, value=1.0):
    cv2.circle(mask, tuple(np.rint(center).astype(int)), int(max(1, radius)),
               float(value), int(width), cv2.LINE_AA)


def _ellipse(mask, center, axes, angle=0.0, width=2, value=1.0):
    cv2.ellipse(mask, tuple(np.rint(center).astype(int)),
                tuple(np.maximum(1, np.rint(axes).astype(int))), float(angle),
                0.0, 360.0, float(value), int(width), cv2.LINE_AA)


def _poly(mask, points, width=2, fill=False, value=1.0):
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    if fill:
        cv2.fillPoly(mask, [pts], float(value), cv2.LINE_AA)
    else:
        cv2.polylines(mask, [pts], True, float(value), int(width), cv2.LINE_AA)


def _phase_line(phase, half=0.18):
    """Fine analytic line at every integer phase; not a random/noise field."""
    d = np.abs(np.sin(np.pi * np.asarray(phase, np.float32)))
    return _f((float(half) - d) / max(0.02, float(half)) + 0.25)


def _interval(v, lo, hi, feather=0.02):
    v = np.asarray(v, np.float32)
    f = max(float(feather), 1.0e-3)
    return _f(np.minimum((v - lo) / f + 0.5, (hi - v) / f + 0.5))


def _distance_to_ink(ink):
    return cv2.distanceTransform((np.asarray(ink) < 0.20).astype(np.uint8),
                                 cv2.DIST_L2, 5).astype(np.float32)


def _finish(masks: Mapping[str, np.ndarray], banks: Mapping[str, str], tone) -> Grammar:
    if len(masks) < 7:
        raise ValueError("WR-B3 lazy grammar: fewer than seven causal marks")
    rows = []
    for name, mask in masks.items():
        u = _f(mask)
        if float(u.std()) < 0.0015:
            raise ValueError(f"WR-B3 flat causal mark {name!r}")
        owner = banks[name]
        if owner not in {"A", "B", "N"}:
            raise ValueError(owner)
        rows.append((name, u, owner))
    if not ({"A", "B"} <= {owner for _name, _mask, owner in rows}):
        raise ValueError("WR-B3 grammar lacks explicit Fractured A/B anatomy")
    return Grammar(tuple(rows), _n(tone))


def _banks(names, pattern="ABN"):
    return {name: pattern[i % len(pattern)] for i, name in enumerate(names)}


def _bezier(p0, p1, p2, p3, count=96):
    t = np.linspace(0.0, 1.0, int(count), dtype=np.float32)[:, None]
    return ((1 - t) ** 3 * np.asarray(p0) + 3 * (1 - t) ** 2 * t * np.asarray(p1)
            + 3 * (1 - t) * t ** 2 * np.asarray(p2) + t ** 3 * np.asarray(p3))


def _power_cells(points, weights=None):
    """Exact deterministic power diagram used by one pollen topology only."""
    pts = np.asarray(points, np.float32)
    if weights is None:
        weights = np.zeros(len(pts), np.float32)
    best = np.full((S, S), np.inf, np.float32)
    second = np.full((S, S), np.inf, np.float32)
    label = np.zeros((S, S), np.int16)
    for i, ((px, py), w) in enumerate(zip(pts, np.asarray(weights, np.float32))):
        d = (X - px) ** 2 + (Y - py) ** 2 - w
        take = d < best
        second = np.where(take, best, np.minimum(second, d))
        label = np.where(take, i, label)
        best = np.where(take, d, best)
    margin = _n(np.sqrt(np.maximum(second - best, 0.0)))
    return label, margin, _n(best)


def _cell_edges(label, width=1):
    lab = np.asarray(label)
    e = np.zeros(lab.shape, np.float32)
    e[:, 1:] = np.maximum(e[:, 1:], lab[:, 1:] != lab[:, :-1])
    e[1:, :] = np.maximum(e[1:, :], lab[1:, :] != lab[:-1, :])
    return _dilate(e, width)


# 01 -- vascular crozier territories, no shared centre or radial emblem.
def w3_magenta_whorl():
    rachis, pinnae, bridges, hooks = _blank(), _blank(), _blank(), _blank()
    scars, fronts, sutures, tissue = _blank(), _blank(), _blank(), _blank()
    xs = np.linspace(-30, 542, 220)
    for j in range(8):
        y = 24 + j * 66 + 15 * np.sin(xs / (37 + 2 * j) + j * 0.9)
        y += 9 * np.sin(xs / 103 + j * 1.7)
        pts = np.c_[xs, y]
        _curve(rachis, pts, 3 + j % 2)
        for k in range(7 + (j % 3)):
            q = 10 + k * 18
            px, py = pts[q]
            side = -1 if (j + k) % 2 else 1
            branch = _bezier((px, py), (px + 12, py + side * 15),
                             (px + 25, py + side * (20 + 2 * k)),
                             (px + 39, py + side * (10 + k)), 28)
            _curve(pinnae, branch, 2)
            if k % 2 == 0:
                _ellipse(hooks, branch[-1], (7 + k % 3, 4 + j % 3),
                         angle=18 * side, width=2)
        if j < 7:
            for k in (28, 73, 118):
                p0 = pts[k]
                p1 = (pts[k, 0] + 18, pts[k, 1] + 31)
                _curve(bridges, _bezier(p0, (p0[0] + 7, p0[1] + 18),
                                        (p1[0] - 7, p1[1] - 17), p1, 24), 2)
    dist = _distance_to_ink(np.maximum(rachis, pinnae))
    tissue[:] = _f((13.0 - dist) / 5.0 + 0.5)
    fronts[:] = _phase_line(dist / 5.5 + 0.08 * np.sin(Y / 27), 0.22) * tissue
    scars[:] = _edge(tissue, 1)
    sutures[:] = _phase_line((X + 0.37 * Y + 10 * np.sin(Y / 41)) / 47, 0.13) * tissue
    m = dict(vascular_rachis=rachis, unequal_pinnae=pinnae, anastomosis_bridges=bridges,
             cropped_crozier_hooks=hooks, tissue_scar_seams=scars,
             nonconcentric_growth_fronts=fronts, oblique_sutures=sutures,
             connected_lamina=tissue)
    return _finish(m, _banks(m, "ABNABBNA"), dist + 0.17 * X + 0.31 * Y)


# 02 -- one grafted climbing graph whose chronology changes across the frame.
def w3_leafvine_drape():
    trunks, grafts, tendrils, blade_ribs = _blank(), _blank(), _blank(), _blank()
    blade_lips, racemes, nodes, cambium = _blank(), _blank(), _blank(), _blank()
    for j, x0 in enumerate((-18, 78, 184, 310, 430, 526)):
        ys = np.linspace(-25, 538, 130)
        xs = x0 + 27 * np.sin(ys / (48 + 3 * j) + 0.7 * j) + 7 * np.sin(ys / 17 + j)
        pts = np.c_[xs, ys]
        _curve(trunks, pts, 3)
        for k in range(8):
            q = 12 + k * 14
            p = pts[q]
            side = -1 if (j + k) % 2 else 1
            tip = (p[0] + side * (34 + 6 * ((j + k) % 3)), p[1] - 8 + 5 * k)
            branch = _bezier(p, (p[0] + side * 13, p[1] - 11),
                             (tip[0] - side * 10, tip[1] + 6), tip, 25)
            _curve(tendrils, branch, 2)
            # Narrow, cropped blade anatomy, not a detached leaf icon.
            n = np.array([-0.35 * side, 1.0], np.float32)
            n /= np.linalg.norm(n)
            a = np.asarray(tip) - n * (8 + (k % 3))
            b = np.asarray(tip) + n * (8 + (k % 3))
            _curve(blade_ribs, (p, tip), 2)
            _curve(blade_lips, _bezier(a, a + side * np.array([9, -7]),
                                       b + side * np.array([9, 7]), b, 26), 2)
            if k % 3 == 1:
                for u in range(3):
                    _circle(racemes, (tip[0] + side * (6 + 5 * u), tip[1] + 5 * u), 2 + u % 2, 2)
            _circle(nodes, p, 3 + (j + k) % 2, 2)
    for j in range(5):
        for y0 in (82 + 73 * j, 118 + 73 * j):
            _curve(grafts, _bezier((30 + 96 * j, y0), (73 + 96 * j, y0 - 28),
                                   (103 + 96 * j, y0 + 30), (131 + 96 * j, y0 + 2), 36), 2)
    cambium[:] = _dilate(np.maximum(trunks, grafts), 6)
    m = dict(climbing_trunks=trunks, continuous_grafts=grafts, unequal_tendrils=tendrils,
             attached_blade_ribs=blade_ribs, blade_lips=blade_lips,
             raceme_channels=racemes, cambium_nodes=nodes, connected_cambium=cambium)
    tone = _distance_to_ink(np.maximum(trunks, tendrils)) + 0.23 * X - 0.11 * Y
    return _finish(m, _banks(m, "ABNABBNN"), tone)


# 03 -- deterministic Gray-Scott pollen-tube tissue; no flower-head icon.
def w3_butter_pollen():
    n = 144
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    u = np.ones((n, n), np.float32)
    v = np.zeros((n, n), np.float32)
    seed = ((np.sin(xx * 0.173 + np.sin(yy * 0.071) * 2.1)
             + np.cos(yy * 0.149 - xx * 0.037)) > 1.05).astype(np.float32)
    v[:] = 0.72 * seed
    u[:] -= 0.48 * seed
    for _ in range(74):
        lu = (np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u)
        lv = (np.roll(v, 1, 0) + np.roll(v, -1, 0) + np.roll(v, 1, 1) + np.roll(v, -1, 1) - 4 * v)
        uvv = u * v * v
        feed = 0.034 + 0.006 * (xx / n)
        kill = 0.060 + 0.004 * (yy / n)
        u = np.clip(u + 0.16 * lu - uvv + feed * (1 - u), 0, 1)
        v = np.clip(v + 0.08 * lv + uvv - (feed + kill) * v, 0, 1)
    q = cv2.resize(_n(v - 0.42 * u), (S, S), interpolation=cv2.INTER_CUBIC)
    membrane = _edge(_interval(q, 0.42, 0.67, 0.025), 1)
    chambers = _interval(q, 0.50, 0.82, 0.035)
    callose = _phase_line(q * 8.0 + X / 91, 0.16) * chambers
    fissures = _phase_line(q * 5.0 - Y / 77, 0.12) * (1 - chambers)
    pores = _f(_phase_line(X / 29 + Y / 47, 0.08) * _phase_line(q * 4.0, 0.10))
    pressure = _edge(_dilate(chambers, 5), 1)
    laterals = _f(_phase_line((X + 0.25 * Y) / 53 + 1.8 * q, 0.12) * chambers)
    septa = _f(_phase_line((Y - 0.17 * X) / 61 - 1.4 * q, 0.10) * chambers)
    m = dict(tube_membranes=membrane, callose_chambers=chambers,
             callose_lamellae=callose, branching_fissures=fissures,
             germ_pore_canals=pores, pressure_fronts=pressure,
             lateral_membranes=laterals, unequal_septa=septa)
    return _finish(m, _banks(m, "ABBNANBA"), q + 0.09 * X + 0.04 * Y)


# 04 -- overlapping edge-entered petal shear territories, never concentric.
def w3_pink_rose():
    shear = (Y - 0.38 * X + 42 * np.sin((X + 31 * np.sin(Y / 73)) / 61)
             + 19 * np.sin((X + Y) / 29))
    territory = 0.5 + 0.5 * np.sin(shear / 22)
    petal_sheets = _interval(territory, 0.18, 0.82, 0.05)
    fold_lips = _phase_line(shear / 44, 0.13)
    counter = X + 0.57 * Y + 33 * np.sin(Y / 49) - 14 * np.sin(X / 37)
    crossing_veins = _phase_line(counter / 26 + 0.3 * np.sin(shear / 53), 0.09) * petal_sheets
    ribs = _phase_line((Y + 18 * np.sin(X / 43)) / 37 + territory, 0.10) * petal_sheets
    tears = _f(_phase_line((X - 1.7 * Y) / 79, 0.08) * fold_lips)
    lips2 = _edge(_interval(territory, 0.33, 0.58, 0.03), 1)
    vascular = _f(_dilate(crossing_veins, 2) * (1 - 0.5 * fold_lips))
    scars = _f(_phase_line((X + Y) / 101 + shear / 81, 0.09) * petal_sheets)
    m = dict(cropped_petal_sheets=petal_sheets, shear_fold_lips=fold_lips,
             crossing_petiole_veins=crossing_veins, lamina_ribs=ribs,
             unequal_tissue_tears=tears, folded_inner_lips=lips2,
             vascular_tributaries=vascular, compression_scars=scars)
    return _finish(m, _banks(m, "ABNABBNA"), shear + 0.7 * counter)


# 05 -- fused coral skeletal continent with cups, forks and bridges.
def w3_coral_cluster():
    trunks, antlers, cups, combs = _blank(), _blank(), _blank(), _blank()
    bridges, pores, cortex, scars = _blank(), _blank(), _blank(), _blank()
    for j in range(11):
        y0 = -25 + j * 54
        pts = _bezier((-28, y0), (115, y0 + 70 * np.sin(j * 1.2)),
                      (330, y0 - 58 * np.cos(j * 0.8)), (540, y0 + 26), 110)
        _curve(trunks, pts, 4 + j % 3)
        for k in range(6):
            p = pts[12 + 16 * k]
            side = -1 if (j + k) % 2 else 1
            tip = p + np.array([25 + 4 * k, side * (22 + 3 * ((j + k) % 4))])
            b = _bezier(p, p + [7, side * 12], tip - [8, side * 5], tip, 24)
            _curve(antlers, b, 2 + k % 2)
            _circle(cups, tip, 4 + (j + k) % 3, 2)
            for h in (-1, 1):
                _curve(combs, (tip, tip + [h * 8, side * 9]), 2)
            if k in (1, 4):
                _circle(pores, p + [9, side * 5], 2 + j % 2, 2)
        if j < 10:
            _curve(bridges, _bezier((88 + 31 * (j % 3), y0 + 18),
                                    (150, y0 + 34), (220, y0 + 30),
                                    (276 + 17 * (j % 4), y0 + 54), 34), 2)
    cortex[:] = _dilate(np.maximum(trunks, antlers), 7)
    scars[:] = _edge(cortex, 1)
    m = dict(fused_skeletal_trunks=trunks, split_antler_forks=antlers,
             unequal_polyp_cups=cups, comb_polyps=combs, skeletal_bridges=bridges,
             cortical_pores=pores, fused_cortex=cortex, growth_scars=scars)
    return _finish(m, _banks(m, "ABNABNAB"), _distance_to_ink(trunks) + 0.41 * X - 0.18 * Y)


# 06 -- nonperiodic botanical marquetry faults, not a fan or shared root.
def w3_butter_mosaic():
    q = (np.sin((0.91 * X + 0.37 * Y) / 19.0)
         + 0.83 * np.sin((-0.29 * X + 1.13 * Y) / 23.0 + 0.7)
         + 0.66 * np.sin((0.71 * X - 0.88 * Y) / 31.0 + 1.9)
         + 0.47 * np.cos((1.31 * X + 0.17 * Y) / 43.0 - 0.4))
    r = (np.sin((X + 1.618 * Y) / 37.0) + np.cos((1.414 * X - Y) / 41.0))
    facets_a = _interval(q, -2.5, -0.45, 0.10)
    facets_b = _interval(q, 0.25, 2.6, 0.10)
    fault_edges = _phase_line(q * 0.73, 0.11)
    cleavage = _phase_line(r * 1.35 + q * 0.18, 0.09)
    vein_anastomoses = _f(_phase_line((X + 0.46 * Y) / 27 + 0.22 * q, 0.09)
                          * (0.25 + 0.75 * facets_a))
    shard_lips = _edge(_interval(r, -0.35, 0.65, 0.05), 1)
    resin_bridges = _f(_dilate(fault_edges, 3) * _phase_line((X - Y) / 67, 0.13))
    tear_notches = _f(cleavage * _phase_line((1.7 * X + Y) / 83, 0.08))
    m = dict(ochre_botanical_shards=facets_a, violet_botanical_shards=facets_b,
             marquetry_fault_edges=fault_edges, oblique_cleavage=cleavage,
             vein_anastomoses=vein_anastomoses, unequal_shard_lips=shard_lips,
             resin_bridges=resin_bridges, tissue_tear_notches=tear_notches)
    return _finish(m, _banks(m, "ABNABNBA"), q + 1.8 * r + 0.05 * X)


# 07 -- full-domain exine power terrain with unequal pores and septa.
def w3_pink_pollen():
    pts = []
    weights = []
    golden = 0.61803398875
    for i in range(58):
        # Low-discrepancy deterministic biology; no random/noise perturbation.
        px = 18 + 476 * ((i * golden + 0.071 * np.sin(i * 1.9)) % 1.0)
        py = 16 + 480 * ((i * golden * golden + 0.053 * np.cos(i * 2.3)) % 1.0)
        pts.append((px, py))
        weights.append(90 * np.sin(i * 0.83) + 45 * np.cos(i * 1.71))
    label, margin, floor = _power_cells(pts, weights)
    walls = _cell_edges(label, 1)
    lips = _f(_dilate(walls, 4) - 0.65 * _dilate(walls, 1))
    chambers_a = ((label % 5) < 2).astype(np.float32)
    chambers_b = ((label % 7) >= 4).astype(np.float32)
    pores, canals = _blank(), _blank()
    for i, p in enumerate(pts):
        rad = 2 + (i * 3) % 5
        _circle(pores, p, rad, 2)
        if i % 3 == 0:
            q = pts[(i * 11 + 7) % len(pts)]
            _curve(canals, _bezier(p, (p[0] + 13, p[1] - 9),
                                   (q[0] - 17, q[1] + 11), q, 28), 2)
    compression = _phase_line(margin * 7.0 + floor * 1.7, 0.12)
    septa = _f(walls * _phase_line((X + 0.31 * Y) / 41, 0.16))
    rupture = _f(canals * _dilate(walls, 3))
    m = dict(exine_septal_walls=walls, rupture_lips=lips,
             compressed_chambers=chambers_a, elastic_chambers=chambers_b,
             unequal_germ_pores=pores, pore_canals=canals,
             compression_lamellae=compression, connected_rupture_fronts=rupture,
             wall_septa=septa)
    return _finish(m, _banks(m, "ABNABBANN"), label + 3.2 * margin + 0.007 * X)


# 08 -- phloem/xylem braids split, merge and fray without a crossing hub.
def w3_white_whorl():
    xylem, phloem, split_seams, merge_plates = _blank(), _blank(), _blank(), _blank()
    frays, valves, crosswalls, sheath = _blank(), _blank(), _blank(), _blank()
    xs = np.linspace(-35, 547, 170)
    for j in range(18):
        base = 16 + j * 29
        phase = j * 0.71
        amp = 8 + 3 * (j % 4)
        y = base + amp * np.sin(xs / (24 + j % 5) + phase)
        y += (5 + j % 3) * np.sin(xs / 67 - phase * 0.4)
        target = xylem if j % 2 == 0 else phloem
        _curve(target, np.c_[xs, y], 2 + (j % 3 == 0))
        for x0 in (74 + 109 * (j % 4), 310 + 43 * (j % 3)):
            q = np.argmin(np.abs(xs - x0))
            p = (xs[q], y[q])
            _curve(split_seams, _bezier(p, (p[0] + 13, p[1] - 14),
                                        (p[0] + 29, p[1] + 17),
                                        (p[0] + 45, p[1] + (-1) ** j * 22), 24), 2)
            _ellipse(valves, (p[0] + 20, p[1]), (5, 3), angle=17 * ((j % 3) - 1), width=2)
        if j < 17 and j % 3 == 1:
            x0 = 105 + 61 * (j % 5)
            _curve(merge_plates, ((x0, base), (x0 + 24, base + 28)), 3)
        for k in range(3):
            x0 = 480 + 8 * k
            q = np.argmin(np.abs(xs - x0))
            _curve(frays, ((xs[q], y[q]), (523, y[q] + (k - 1) * 11 + (j % 3) * 3)), 2)
    bundle = np.maximum(xylem, phloem)
    sheath[:] = _dilate(bundle, 5)
    crosswalls[:] = _f(_phase_line((X + 0.09 * Y) / 73, 0.11) * sheath)
    m = dict(xylem_braids=xylem, phloem_braids=phloem, unequal_split_seams=split_seams,
             reconnect_plates=merge_plates, frayed_fibres=frays, vessel_valves=valves,
             transverse_crosswalls=crosswalls, living_bundle_sheath=sheath)
    return _finish(m, _banks(m, "ABNABBNA"), _distance_to_ink(bundle) + 0.31 * X + 0.13 * Y)


# 09 -- canvas-filling filament tissue with attached anther cutaways.
def w3_coral_stamen():
    bundles, connective, side_sprays, locules = _blank(), _blank(), _blank(), _blank()
    pollen_channels, wall_pleats, bifurcations, membranes = _blank(), _blank(), _blank(), _blank()
    ys = np.linspace(-30, 542, 155)
    for j in range(13):
        x = 18 + j * 42 + 18 * np.sin(ys / (53 + j % 4) + j * 0.57)
        x += 5 * np.sin(ys / 19 - j * 0.31)
        pts = np.c_[x, ys]
        _curve(bundles, pts, 3 + j % 2)
        for k in range(7):
            q = 12 + k * 19
            p = pts[q]
            side = -1 if (j + k) % 2 else 1
            tip = p + [side * (20 + 4 * (k % 3)), 11 + 3 * (j % 3)]
            _curve(side_sprays, _bezier(p, p + [side * 7, 5], tip - [side * 5, 4], tip, 20), 2)
            if k % 2 == 0:
                _ellipse(locules, tip, (6 + k % 3, 3 + j % 2), angle=78, width=2)
                _curve(pollen_channels, ((tip[0] - 5, tip[1]), (tip[0] + 5, tip[1])), 2)
            if k % 3 == 1:
                _curve(bifurcations, (p, p + [side * 15, -13], p + [side * 26, -4]), 2)
    for y0 in (58, 131, 224, 337, 453):
        pts = np.c_[np.linspace(-20, 532, 90),
                    y0 + 13 * np.sin(np.linspace(-20, 532, 90) / 42 + y0 / 37)]
        _curve(connective, pts, 3)
    membranes[:] = _dilate(np.maximum(bundles, connective), 7)
    wall_pleats[:] = _phase_line((Y + 0.21 * X) / 17, 0.08) * membranes
    m = dict(filament_bundles=bundles, connective_tissue=connective,
             attached_side_sprays=side_sprays, micro_anther_locules=locules,
             pollen_channels=pollen_channels, wall_pleats=wall_pleats,
             unequal_bifurcations=bifurcations, continuous_membranes=membranes)
    return _finish(m, _banks(m, "ABNABBNN"), _distance_to_ink(bundles) + 0.12 * X - 0.44 * Y)


# 10 -- irregular cropped rose-thicket chambers, explicitly nonradial.
def w3_lilac_rose():
    walls, thorn_ribs, lips, tears = _blank(), _blank(), _blank(), _blank()
    vascular, grafts, chamber_a, chamber_b = _blank(), _blank(), _blank(), _blank()
    centers = [(-45, 72), (89, -36), (226, 38), (431, -52), (548, 105),
               (505, 298), (548, 492), (333, 551), (132, 523), (-58, 405),
               (37, 246), (258, 262), (397, 178), (170, 354)]
    for i, c in enumerate(centers):
        axes = (69 + 13 * (i % 4), 42 + 9 * ((i * 3) % 5))
        angle = 17 + 29 * (i % 6)
        target = chamber_a if i % 2 == 0 else chamber_b
        cv2.ellipse(target, tuple(map(int, c)), axes, angle, 0, 360, 1.0, -1, cv2.LINE_AA)
        _ellipse(walls, c, axes, angle, 3)
        _ellipse(lips, c, (axes[0] - 8, axes[1] - 6), angle + 6, 2)
        th = np.deg2rad(angle)
        for k in range(5):
            p0 = np.asarray(c, np.float32) + [np.cos(th) * (k - 2) * 9, np.sin(th) * (k - 2) * 9]
            p1 = p0 + [np.cos(th + 1.2) * axes[1], np.sin(th + 1.2) * axes[1]]
            _curve(thorn_ribs, (p0, p1), 2)
        if i < len(centers) - 1:
            d = centers[(i + 3) % len(centers)]
            _curve(grafts, _bezier(c, (c[0] + 23, c[1] - 18),
                                   (d[0] - 31, d[1] + 17), d, 34), 2)
    vascular[:] = _f(thorn_ribs * _dilate(np.maximum(chamber_a, chamber_b), 2))
    tears[:] = _f(walls * _phase_line((X - 1.3 * Y) / 71, 0.10))
    m = dict(interlocking_chamber_walls=walls, thorned_petal_ribs=thorn_ribs,
             folded_chamber_lips=lips, unequal_tissue_tears=tears,
             vascular_faults=vascular, chamber_grafts=grafts,
             compressed_petal_tissue=chamber_a, translucent_petal_tissue=chamber_b)
    return _finish(m, _banks(m, "ABNABNAB"), _distance_to_ink(walls) + 0.21 * X + 0.19 * Y)


# 11 -- recursive crown enters from four edges and fuses through grafts.
def w3_coral_vine():
    limbs, twigs, grafts, tendrils = _blank(), _blank(), _blank(), _blank()
    leaf_ribs, leaf_lips, nodes, cambium = _blank(), _blank(), _blank(), _blank()

    def grow(p, angle, length, depth, phase):
        direction = np.array([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.array([-direction[1], direction[0]], np.float32)
        end = np.asarray(p, np.float32) + direction * length + normal * (7 * np.sin(phase))
        ctrl1 = np.asarray(p) + direction * length * 0.31 + normal * (10 * np.cos(phase * 1.7))
        ctrl2 = np.asarray(p) + direction * length * 0.70 - normal * (8 * np.sin(phase * 1.3))
        path = _bezier(p, ctrl1, ctrl2, end, 26)
        _curve(limbs if depth >= 3 else twigs, path, 2 + (depth >= 4) + (depth >= 5))
        _circle(nodes, end, 2 + depth % 3, 2)
        if depth <= 0:
            for side in (-1, 1):
                tip = end + normal * side * (8 + 2 * (int(abs(phase) * 7) % 3))
                _curve(leaf_ribs, (end, tip), 2)
                _ellipse(leaf_lips, tip, (7, 3), angle=np.rad2deg(angle) + side * 31, width=2)
            return end
        a = grow(end, angle - (0.31 + 0.035 * depth), length * 0.73, depth - 1, phase + 0.83)
        b = grow(end, angle + (0.44 - 0.028 * depth), length * 0.66, depth - 1, phase + 1.47)
        if depth in (2, 4):
            _curve(grafts, _bezier(a, a + [9, -7], b + [-11, 8], b, 18), 2)
        if depth == 1:
            _curve(tendrils, _bezier(end, end + normal * 11, end + direction * 16 - normal * 13,
                                     end + direction * 24, 22), 2)
        return end

    grow((-28, 78), 0.14, 101, 5, 0.7)
    grow((538, 194), 3.02, 94, 5, 1.8)
    grow((171, -24), 1.19, 88, 5, 2.7)
    grow((356, 538), -1.73, 92, 5, 3.9)
    cambium[:] = _dilate(np.maximum(limbs, twigs), 5)
    m = dict(cropped_primary_limbs=limbs, tapered_crown_twigs=twigs,
             living_graft_bridges=grafts, unequal_tendrils=tendrils,
             attached_leaf_ribs=leaf_ribs, narrow_leaf_lips=leaf_lips,
             cambium_nodes=nodes, fused_cambium=cambium)
    return _finish(m, _banks(m, "ABNABBNA"), _distance_to_ink(np.maximum(limbs, twigs)) + 0.29 * X - 0.33 * Y)


# 12 -- one full-frame asymmetric anther cutaway, not detached locule blobs.
def w3_lilac_stamen():
    axis = Y - 0.26 * X + 27 * np.sin(X / 58) + 11 * np.sin((X + Y) / 31)
    wall = _phase_line(axis / 37, 0.15)
    lobe_phase = axis / 73 + 0.46 * np.sin((X - 0.7 * Y) / 67)
    locule_a = _interval(np.mod(lobe_phase, 2.0), 0.12, 0.82, 0.04)
    locule_b = _interval(np.mod(lobe_phase, 2.0), 1.08, 1.78, 0.04)
    connective = _phase_line((X + 0.11 * Y + 24 * np.sin(Y / 79)) / 91, 0.14)
    pleats = _phase_line((Y + 0.43 * X) / 19 + 0.2 * np.sin(axis / 23), 0.08)
    canals = _f(_phase_line((X - 0.16 * Y) / 29 + lobe_phase, 0.09) * (locule_a + locule_b))
    pores = _f(_phase_line(X / 23 + Y / 61, 0.08) * _phase_line(lobe_phase * 3.0, 0.09))
    ruptures = _f(wall * _phase_line((X + Y) / 53, 0.10))
    vascular = _dilate(_f(connective * pleats), 2)
    m = dict(continuous_locule_a=locule_a, continuous_locule_b=locule_b,
             locule_walls=wall, connective_folds=connective,
             vascular_pleats=pleats, pollen_channels=canals,
             unequal_pore_cutaways=pores, rupture_lips=ruptures,
             filament_vascular_bundles=vascular)
    return _finish(m, _banks(m, "ABNABBNAN"), axis + 43 * connective + 17 * pleats)


# 13 -- deterministic Delaunay orchid marquetry, no radial four-petal emblem.
def w3_magenta_mosaic():
    subdiv = cv2.Subdiv2D((0, 0, S, S))
    points = []
    for i in range(72):
        px = 7 + 498 * ((i * 0.754877666 + 0.031 * np.sin(i * 2.1)) % 1.0)
        py = 7 + 498 * ((i * 0.569840296 + 0.027 * np.cos(i * 1.7)) % 1.0)
        p = (float(px), float(py))
        points.append(p)
        subdiv.insert(p)
    edges, facets_a, facets_b, lips = _blank(), _blank(), _blank(), _blank()
    veins, tears, bridges, punctures = _blank(), _blank(), _blank(), _blank()
    tri_rows = []
    for row in subdiv.getTriangleList():
        tri = np.asarray(row, np.float32).reshape(3, 2)
        if np.all((tri[:, 0] >= 0) & (tri[:, 0] < S) & (tri[:, 1] >= 0) & (tri[:, 1] < S)):
            tri_rows.append(tri)
    tri_rows.sort(key=lambda t: (float(t[:, 1].mean()), float(t[:, 0].mean())))
    for i, tri in enumerate(tri_rows):
        _poly(edges, tri, 2)
        target = facets_a if (i * 7) % 11 < 5 else facets_b
        _poly(target, tri, fill=True, value=0.42 + 0.08 * (i % 6))
        centroid = tri.mean(axis=0)
        for vertex in tri:
            _curve(veins, (centroid, 0.65 * centroid + 0.35 * vertex), 2)
        if i % 4 == 0:
            inner = centroid + 0.78 * (tri - centroid)
            _poly(lips, inner, 2)
        if i % 7 == 2:
            _curve(tears, (tri[0], centroid, tri[1]), 2)
        if i % 9 == 3:
            _circle(punctures, centroid, 2 + i % 3, 2)
    bridges[:] = _f(_dilate(edges, 3) * _phase_line((X - 0.63 * Y) / 59, 0.11))
    m = dict(orchid_facets_a=facets_a, orchid_facets_b=facets_b,
             nonradial_fault_edges=edges, folded_facet_lips=lips,
             internal_facet_veins=veins, unequal_tissue_tears=tears,
             resin_fault_bridges=bridges, marquetry_punctures=punctures)
    return _finish(m, _banks(m, "ABNABBNA"), _distance_to_ink(edges) + 0.17 * X + 0.27 * Y)


# 14 -- a single rhizome continent carrying continuous mixed anatomy.
def w3_leaf_whorl():
    rhizome, secondary, blade_tissue, blade_ribs = _blank(), _blank(), _blank(), _blank()
    pitcher_lips, croziers, tendrils, scars = _blank(), _blank(), _blank(), _blank()
    anchors = [(-30, 282), (34, 185), (121, 231), (177, 107), (266, 166),
               (342, 72), (403, 198), (542, 116), (471, 293), (526, 414),
               (387, 371), (318, 511), (211, 419), (94, 523), (-18, 431)]
    for i in range(len(anchors) - 1):
        p, q = np.asarray(anchors[i], np.float32), np.asarray(anchors[i + 1], np.float32)
        d = q - p
        n = np.array([-d[1], d[0]], np.float32)
        n /= max(np.linalg.norm(n), 1.0)
        path = _bezier(p, p + 0.28 * d + n * (17 * (-1) ** i),
                       p + 0.72 * d - n * (13 + 3 * (i % 4)), q, 30)
        _curve(rhizome, path, 4 + i % 3)
        for k in (9, 19):
            base = path[k]
            side = -1 if (i + k) % 2 else 1
            tip = base + n * side * (26 + 4 * (i % 4)) + d / max(np.linalg.norm(d), 1.0) * 9
            _curve(secondary, _bezier(base, base + n * side * 8,
                                      tip - n * side * 6, tip, 20), 2)
            if i % 4 == 0:
                _ellipse(pitcher_lips, tip, (8, 4), angle=np.rad2deg(np.arctan2(d[1], d[0])), width=2)
            elif i % 4 == 1:
                _ellipse(croziers, tip, (9, 6), angle=37 * side, width=2)
            elif i % 4 == 2:
                _curve(tendrils, _bezier(tip, tip + n * side * 9,
                                         tip - n * side * 11 + d * 0.1, tip + d * 0.2, 24), 2)
            else:
                _ellipse(blade_tissue, tip, (15, 6), angle=np.rad2deg(np.arctan2(d[1], d[0])), width=-1)
                _curve(blade_ribs, (base, tip), 2)
    body = _dilate(np.maximum(rhizome, secondary), 6)
    blade_tissue[:] = np.maximum(blade_tissue, body)
    scars[:] = _f(_edge(body, 1) * _phase_line((X + Y) / 61, 0.16))
    m = dict(continuous_rhizome=rhizome, attached_secondary_axes=secondary,
             shared_living_tissue=blade_tissue, blade_vascular_ribs=blade_ribs,
             pitcher_cutaway_lips=pitcher_lips, cropped_crozier_folds=croziers,
             unequal_tendrils=tendrils, rhizome_growth_scars=scars)
    return _finish(m, _banks(m, "ABNABBNA"), _distance_to_ink(rhizome) + 0.37 * X - 0.12 * Y)


# 15 -- wind-sheared exine folds with pore chains and rupture tributaries.
def w3_white_pollen():
    flow = (0.78 * X + 0.42 * Y + 24 * np.sin(Y / 47)
            + 9 * np.sin((X - Y) / 29))
    fold_ridges = _phase_line(flow / 18, 0.11)
    fold_webs = _phase_line((Y - 0.31 * X + 16 * np.sin(X / 53)) / 27, 0.09)
    septa = _f(fold_ridges * _dilate(fold_webs, 2))
    pore_chains = _f(_phase_line(flow / 31, 0.09)
                     * _phase_line((X - 1.9 * Y) / 43, 0.08))
    rupture = _f(_phase_line((X + 0.13 * Y) / 97 + 0.5 * np.sin(Y / 61), 0.11)
                  * (0.35 + 0.65 * fold_ridges))
    tributaries = _f(_dilate(rupture, 3) * _phase_line((Y + X) / 39, 0.10))
    tension_a = _interval(np.sin(flow / 34), -1.0, -0.12, 0.05)
    tension_b = _interval(np.sin(flow / 34), 0.18, 1.0, 0.05)
    lips = _edge(_dilate(rupture, 5), 1)
    m = dict(wind_shear_fold_ridges=fold_ridges, transverse_fold_webs=fold_webs,
             unequal_septa=septa, germ_pore_chains=pore_chains,
             primary_rupture_fronts=rupture, rupture_tributaries=tributaries,
             compressed_exine=tension_a, stretched_exine=tension_b,
             rupture_lips=lips)
    return _finish(m, _banks(m, "ABNABBNAN"), flow + 29 * fold_webs)


# 16 -- dense longitudinal stamen organ with hundreds of attached chambers.
def w3_pink_stamen():
    mid = 246 + 43 * np.sin((X - 34) / 87) + 17 * np.sin(X / 31)
    rel = Y - mid
    connective = _f((34 - np.abs(rel)) / 7 + 0.5)
    connective_walls = _phase_line(rel / 19, 0.13) * connective
    filaments, locules, locule_walls, pollen = _blank(), _blank(), _blank(), _blank()
    crossveins, sutures = _blank(), _blank()
    for j, x0 in enumerate(range(-18, 548, 23)):
        yc = float(246 + 43 * np.sin((x0 - 34) / 87) + 17 * np.sin(x0 / 31))
        for side in (-1, 1):
            y0 = yc + side * (48 + 12 * ((j * 3) % 5))
            axes = (8 + j % 4, 13 + (j * 2) % 5)
            _ellipse(locules, (x0, y0), axes, angle=side * (18 + j % 13), width=-1, value=0.72)
            _ellipse(locule_walls, (x0, y0), axes, angle=side * (18 + j % 13), width=2)
            _curve(filaments, _bezier((x0, yc + side * 17),
                                      (x0 - 7, yc + side * 31),
                                      (x0 + 6, y0 - side * 10), (x0, y0), 22), 2)
            for k in (-1, 0, 1):
                _circle(pollen, (x0 + 3 * k, y0 + side * (2 + 4 * k)), 2, 2)
            if j % 2 == 0:
                _curve(crossveins, ((x0 - 9, y0), (x0 + 9, y0 + side * 4)), 2)
        if j % 3 == 1:
            _curve(sutures, ((x0, yc - 28), (x0 + 11, yc + 28)), 2)
    vascular = _f(_dilate(filaments, 3) * (0.35 + 0.65 * connective))
    m = dict(continuous_connective=connective, connective_crosswalls=connective_walls,
             filament_bundles=filaments, attached_locule_tissue=locules,
             locule_walls=locule_walls, pollen_microchannels=pollen,
             unequal_crossveins=crossveins, dehiscence_sutures=sutures,
             vascular_shoulders=vascular)
    return _finish(m, _banks(m, "ABNABBNAN"), rel + 19 * locules + 0.14 * X)


# 17 -- tectonic petal basins entered from edges, not one enclosing rose blob.
def w3_blush_rose():
    sources = [(-112, 44, 158, 93, 0.7), (87, -96, 122, 174, -0.4),
               (372, -118, 191, 109, 0.9), (619, 112, 146, 205, -0.8),
               (586, 423, 182, 118, 0.3), (284, 633, 207, 139, -0.5),
               (-103, 528, 171, 211, 0.6), (-72, 267, 116, 154, -0.9),
               (250, 218, 132, 87, 0.2)]
    fields = []
    for cx, cy, ax, ay, ang in sources:
        ca, sa = np.cos(ang), np.sin(ang)
        xx = (X - cx) * ca + (Y - cy) * sa
        yy = -(X - cx) * sa + (Y - cy) * ca
        fields.append((np.abs(xx / ax) ** 2.7 + np.abs(yy / ay) ** 2.1).astype(np.float32))
    stack = np.stack(fields)
    order = np.argsort(stack, axis=0)
    label = order[0].astype(np.int16)
    d1 = np.take_along_axis(stack, order[:1], axis=0)[0]
    d2 = np.take_along_axis(stack, order[1:2], axis=0)[0]
    basin_walls = _cell_edges(label, 1)
    folded_lips = _f(_phase_line(d1 * 4.1, 0.12) * (d1 < 1.7))
    rib_tributaries = _f(_phase_line((X + 0.43 * Y) / 31 + 0.7 * d1, 0.09)
                         * (d1 < 1.55))
    vascular_loops = _f(_phase_line((d2 - d1) * 2.8, 0.11) * (d1 < 1.8))
    tears = _f(basin_walls * _phase_line((X - 1.2 * Y) / 73, 0.10))
    tissue_a = ((label % 3) == 0).astype(np.float32) * _f((1.8 - d1) / 0.25)
    tissue_b = ((label % 3) != 0).astype(np.float32) * _f((1.8 - d1) / 0.25)
    compression = _phase_line((d2 - d1) * 5.0 + d1, 0.10)
    scars = _edge(_dilate(tears, 4), 1)
    m = dict(interlocking_basin_walls=basin_walls, folded_petal_lips=folded_lips,
             rib_tributaries=rib_tributaries, vascular_fold_loops=vascular_loops,
             unequal_tissue_tears=tears, compressed_petal_basins=tissue_a,
             translucent_petal_basins=tissue_b, compression_lamellae=compression,
             healed_tear_scars=scars)
    return _finish(m, _banks(m, "ABNABBNAN"), label + 2.7 * d1 + 0.13 * X)


# 18 -- gravity-grown canopy with lateral grafts filling every calm zone.
def w3_lilac_vine():
    drapes, laterals, grafts, tendrils = _blank(), _blank(), _blank(), _blank()
    leaf_ribs, blade_lips, racemes, nodes = _blank(), _blank(), _blank(), _blank()
    for j, x0 in enumerate((-22, 34, 102, 181, 273, 369, 458, 529)):
        length = 390 + 17 * ((j * 5) % 7)
        ys = np.linspace(-25, min(548, length), 120)
        xs = x0 + (13 + 4 * (j % 3)) * np.sin(ys / (41 + 2 * j) + j * 0.8)
        xs += 5 * np.sin(ys / 17 - j * 0.47)
        pts = np.c_[xs, ys]
        _curve(drapes, pts, 3 + j % 2)
        for k in range(9):
            q = 10 + k * 11
            p = pts[q]
            side = -1 if (j + k) % 2 else 1
            tip = p + [side * (24 + 5 * ((j + 2 * k) % 4)), 13 + 4 * (k % 3)]
            _curve(laterals, _bezier(p, p + [side * 8, 5], tip - [side * 6, 6], tip, 20), 2)
            _curve(leaf_ribs, (p, tip), 2)
            _ellipse(blade_lips, tip, (8 + k % 4, 3 + j % 3), angle=side * 27, width=2)
            _circle(nodes, p, 2 + (j + k) % 3, 2)
            if k % 3 == 1:
                for u in range(3):
                    _circle(racemes, (tip[0] + side * (5 + 5 * u), tip[1] + 5 * u), 2, 2)
            if k % 4 == 2:
                _curve(tendrils, _bezier(tip, tip + [side * 9, 8],
                                         tip + [-side * 8, 16], tip + [side * 3, 24], 24), 2)
    for y0, offset in ((71, 0), (166, 1), (278, 0), (403, 1)):
        for j in range(offset, 7, 2):
            a = (28 + j * 68, y0 + 9 * np.sin(j))
            b = (100 + j * 61, y0 + 18 * np.cos(j * 0.8))
            _curve(grafts, _bezier(a, (a[0] + 17, a[1] - 14),
                                   (b[0] - 19, b[1] + 13), b, 30), 2)
    m = dict(gravity_drapes=drapes, unequal_lateral_axes=laterals,
             canopy_graft_bridges=grafts, curled_tendrils=tendrils,
             attached_leaf_ribs=leaf_ribs, blade_lips=blade_lips,
             raceme_channels=racemes, cambium_nodes=nodes)
    return _finish(m, _banks(m, "ABNABBNA"), _distance_to_ink(drapes) + 0.09 * X - 0.47 * Y)


# 19 -- multiple ascending phyllotactic axes with split bracts and bridges.
def w3_butter_whorl():
    axes, side_axes, bract_ribs, bract_lips = _blank(), _blank(), _blank(), _blank()
    bridges, scars, nodes, sheath = _blank(), _blank(), _blank(), _blank()
    roots = [(-35, 481, -0.83), (71, 542, -1.09), (219, 530, -1.31),
             (391, 547, -1.72), (548, 458, -2.07)]
    for j, (x0, y0, ang) in enumerate(roots):
        t = np.linspace(0, 1, 145)
        length = 610
        x = x0 + length * t * np.cos(ang) + 22 * np.sin(t * 8.7 + j)
        y = y0 + length * t * np.sin(ang) + 14 * np.sin(t * 13.1 - j * 0.6)
        pts = np.c_[x, y]
        _curve(axes, pts, 4 + j % 2)
        for k in range(11):
            q = 10 + k * 11
            p = pts[q]
            tangent = pts[min(q + 2, len(pts) - 1)] - pts[max(q - 2, 0)]
            tangent /= max(np.linalg.norm(tangent), 1.0)
            normal = np.array([-tangent[1], tangent[0]])
            side = -1 if (j + k) % 2 else 1
            tip = p + normal * side * (24 + 4 * (k % 4)) + tangent * 8
            _curve(side_axes, _bezier(p, p + normal * side * 8,
                                      tip - normal * side * 6, tip, 22), 2)
            _curve(bract_ribs, (p, tip), 2)
            poly = [tip, tip - tangent * 8 + normal * side * 5,
                    tip - tangent * 18, tip - tangent * 8 - normal * side * 5]
            _poly(bract_lips, poly, 2)
            _circle(nodes, p, 3, 2)
            if k in (3, 7):
                _curve(scars, (p - normal * 6, p + normal * 6), 2)
        if j < len(roots) - 1:
            a = pts[57 + 7 * j]
            b = (roots[j + 1][0] + 22, roots[j + 1][1] - 131)
            _curve(bridges, _bezier(a, a + [23, -17], np.asarray(b) + [-21, 18], b, 30), 2)
    sheath[:] = _dilate(np.maximum(axes, side_axes), 5)
    m = dict(ascending_primary_axes=axes, causally_attached_side_axes=side_axes,
             split_bract_ribs=bract_ribs, folded_bract_lips=bract_lips,
             vascular_bridges=bridges, growth_scars=scars,
             phyllotactic_nodes=nodes, continuous_axis_sheath=sheath)
    return _finish(m, _banks(m, "ABNABBNA"), _distance_to_ink(axes) + 0.38 * X + 0.31 * Y)


# 20 -- five-attractor Newton exine; global fissure arbor, no perimeter blob.
def w3_magenta_pollen():
    zx = (X - 253.0) / 168.0
    zy = (Y - 267.0) / 173.0
    z = (zx + 1j * zy) * np.exp(1j * (0.19 + 0.07 * np.sin(zx * 1.3)))
    escaped = np.zeros((S, S), np.float32)
    for i in range(19):
        denom = 5.0 * z ** 4
        denom = np.where(np.abs(denom) < 1.0e-6, 1.0e-6 + 0j, denom)
        step = (z ** 5 - 1.0) / denom
        z = z - step
        escaped += (np.abs(step) > 0.0025).astype(np.float32)
    roots = np.exp(2j * np.pi * np.arange(5) / 5.0)
    distances = np.stack([np.abs(z - root) for root in roots])
    label = np.argmin(distances, axis=0).astype(np.int16)
    boundary = _cell_edges(label, 1)
    basin_a = ((label == 0) | (label == 3)).astype(np.float32)
    basin_b = ((label == 1) | (label == 4)).astype(np.float32)
    neutral = (label == 2).astype(np.float32)
    convergence = _n(escaped)
    fold_webs = _phase_line(convergence * 7.3 + np.angle(z) / np.pi, 0.11)
    pore_chains = _f(_phase_line(escaped / 3.7, 0.10)
                     * _phase_line((X + 0.41 * Y) / 47, 0.08))
    bridges = _f(_dilate(boundary, 4) * _phase_line((X - Y) / 71, 0.12))
    rupture_lips = _edge(_dilate(boundary, 5), 1)
    shards = _f(fold_webs * (0.3 + 0.7 * neutral))
    m = dict(magenta_attractor_membrane=basin_a, cyan_attractor_membrane=basin_b,
             neutral_exine_territory=neutral, global_fissure_arbor=boundary,
             convergence_fold_webs=fold_webs, germ_pore_chains=pore_chains,
             exine_fault_bridges=bridges, rupture_lips=rupture_lips,
             internal_membrane_shards=shards)
    return _finish(m, _banks(m, "ABNABBNAN"), label + 0.31 * escaped + 0.17 * np.angle(z))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fbl_magenta_whorl": w3_magenta_whorl,
    "fbl_leafvine_drape": w3_leafvine_drape,
    "fbl_butter_pollen": w3_butter_pollen,
    "fbl_pink_rose": w3_pink_rose,
    "fbl_coral_cluster": w3_coral_cluster,
    "fbl_butter_mosaic": w3_butter_mosaic,
    "fbl_pink_pollen": w3_pink_pollen,
    "fbl_white_whorl": w3_white_whorl,
    "fbl_coral_stamen": w3_coral_stamen,
    "fbl_lilac_rose": w3_lilac_rose,
    "fbl_coral_vine": w3_coral_vine,
    "fbl_lilac_stamen": w3_lilac_stamen,
    "fbl_magenta_mosaic": w3_magenta_mosaic,
    "fbl_leaf_whorl": w3_leaf_whorl,
    "fbl_white_pollen": w3_white_pollen,
    "fbl_pink_stamen": w3_pink_stamen,
    "fbl_blush_rose": w3_blush_rose,
    "fbl_lilac_vine": w3_lilac_vine,
    "fbl_butter_whorl": w3_butter_whorl,
    "fbl_magenta_pollen": w3_magenta_pollen,
}


if len(BUILDERS) != 20 or len({fn.__name__ for fn in BUILDERS.values()}) != 20:
    raise AssertionError("WR-B3 must own twenty distinct topology constructors")


__all__ = ["BUILDERS", "Grammar"]
