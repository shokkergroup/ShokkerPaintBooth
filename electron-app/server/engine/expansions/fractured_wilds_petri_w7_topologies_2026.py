# -*- coding: utf-8 -*-
"""WR-P7 physical-process reset for the three rejected Petri W6 cards.

The visible carriers from W6 are forbidden here.  Culture is rendered from a
recorded multi-lineage Eden accretion history, Garden from a true DLA field,
and Diatom from a continuous dislocated silica-diffraction phase.  Stochastic
choices inside Eden/DLA alter the simulated growth itself; no random/noise
texture is composited afterward to manufacture uniqueness.

SPB-WILDS 2026-08-24, WR-P7.  Isolated candidate; not production-wired and no
owner acceptance is claimed.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np

from engine.expansions import fractured_wilds_petri_w6_topologies_2026 as w6
from engine.paint_v2.exotic_packs.pack_physical_fields import dla_aggregate


w5, w4 = w6.w5, w6.w4
S, X, Y, U, V, TAU = w4.S, w4.X, w4.Y, w4.U, w4.V, w4.TAU
Grammar = w4.Grammar
_f, _n = w4._f, w4._n
_soft_gt, _band, _phase_band = w4._soft_gt, w4._band, w4._phase_band
_edge, _dilate, _erode, _halo = w4._edge, w4._dilate, w4._erode, w4._halo
_curve, _line, _circle, _ellipse, _bezier = (
    w4._curve, w4._line, w4._circle, w4._ellipse, w4._bezier
)
_literal_spec, _finish = w4._literal_spec, w4._finish


def _phase01(value):
    return np.mod(np.asarray(value, np.float32), 1.0)


def _resize_scalar(field, interpolation=cv2.INTER_LINEAR):
    return cv2.resize(np.asarray(field, np.float32), (S, S),
                      interpolation=interpolation).astype(np.float32)


def _label_edges(labels):
    lab = np.asarray(labels)
    out = np.zeros(lab.shape, np.float32)
    out[:, 1:] = np.maximum(out[:, 1:], lab[:, 1:] != lab[:, :-1])
    out[1:, :] = np.maximum(out[1:, :], lab[1:, :] != lab[:-1, :])
    out[1:, 1:] = np.maximum(out[1:, 1:], lab[1:, 1:] != lab[:-1, :-1])
    return out


# ---------------------------------------------------------------------------
# Lime Culture: recorded multi-lineage Eden growth.


def _eden_history(res=184, seed=0x51B7):
    rng = np.random.default_rng(seed)
    occupied = np.zeros((res, res), np.uint8)
    lineage = np.full((res, res), -1, np.int16)
    generation = np.zeros((res, res), np.int16)
    birth_time = np.zeros((res, res), np.float32)
    birth_axis = np.zeros((res, res), np.uint8)
    lineage_bank = []
    frontier = []
    frontier_pos = {}

    seeds = ((16, 20), (45, 151), (72, 78), (102, 169), (132, 27),
             (157, 112), (19, 99), (92, 17), (166, 166))

    def has_empty(y, x):
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1),
                       (-1, -1), (-1, 1), (1, -1), (1, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < res and 0 <= nx < res and not occupied[ny, nx]:
                return True
        return False

    def add_frontier(y, x):
        key = y * res + x
        if key not in frontier_pos:
            frontier_pos[key] = len(frontier)
            frontier.append((y, x))

    def remove_frontier(index):
        y, x = frontier[index]
        key = y * res + x
        last = frontier.pop()
        del frontier_pos[key]
        if index < len(frontier):
            frontier[index] = last
            frontier_pos[last[0] * res + last[1]] = index

    for i, (y, x) in enumerate(seeds):
        occupied[y, x] = 1
        lineage[y, x] = i
        generation[y, x] = 0
        birth_time[y, x] = i + 1
        lineage_bank.append(i & 1)
        add_frontier(y, x)

    count = len(seeds)
    target = int(res * res * .986)
    mutation_budget = 17
    while count < target and frontier:
        # Eden growth: choose a living perimeter cell, then one empty neighbor.
        fi = int(rng.integers(0, len(frontier)))
        y, x = frontier[fi]
        empties = []
        for axis, (dy, dx) in enumerate(((-1, 0), (1, 0), (0, -1), (0, 1),
                                         (-1, -1), (-1, 1), (1, -1), (1, 1))):
            ny, nx = y + dy, x + dx
            if 0 <= ny < res and 0 <= nx < res and not occupied[ny, nx]:
                empties.append((ny, nx, axis))
        if not empties:
            remove_frontier(fi)
            continue

        # Directional persistence is inherited from the birth axis, while a
        # small deterministic nutrient bias favours different fronts.  Both
        # choices affect which cell is born; neither is an image overlay.
        inherited = int(birth_axis[y, x])
        scores = []
        for ny, nx, axis in empties:
            persistence = 1.7 if axis == inherited and generation[y, x] > 2 else 1.0
            nutrient = (1.0 + .28 * np.sin(nx * .113 + ny * .071)
                        + .16 * np.cos(nx * .047 - ny * .137))
            scores.append(max(.08, persistence * nutrient))
        probabilities = np.asarray(scores, np.float64)
        probabilities /= probabilities.sum()
        ny, nx, axis = empties[int(rng.choice(len(empties), p=probabilities))]

        parent_lineage = int(lineage[y, x])
        child_lineage = parent_lineage
        if (mutation_budget > 0 and count > res * res * .14
                and rng.random() < .00072):
            child_lineage = len(lineage_bank)
            lineage_bank.append(1 - lineage_bank[parent_lineage])
            mutation_budget -= 1

        occupied[ny, nx] = 1
        lineage[ny, nx] = child_lineage
        generation[ny, nx] = generation[y, x] + 1
        birth_time[ny, nx] = count
        birth_axis[ny, nx] = axis
        count += 1
        add_frontier(ny, nx)
        if not has_empty(y, x):
            pos = frontier_pos.get(y * res + x)
            if pos is not None:
                remove_frontier(pos)

    bank_lut = np.asarray(lineage_bank, np.uint8)
    valid = lineage >= 0
    banks = np.zeros_like(occupied)
    banks[valid] = bank_lut[lineage[valid]]
    return occupied, lineage, banks, generation, birth_time, birth_axis


def w7_lime_culture() -> Grammar:
    occupied, lineage_small, bank_small, generation_small, birth_small, axis_small = _eden_history()
    valid = occupied.astype(np.float32)
    parent = _resize_scalar((bank_small == 0).astype(np.float32) * valid,
                            cv2.INTER_NEAREST)
    mutant = _resize_scalar((bank_small == 1).astype(np.float32) * valid,
                            cv2.INTER_NEAREST)
    generation = _resize_scalar(generation_small, cv2.INTER_LINEAR)
    birth = _resize_scalar(birth_small, cv2.INTER_LINEAR)
    axes = _resize_scalar(axis_small, cv2.INTER_NEAREST)
    clone_edges = _resize_scalar(_label_edges(lineage_small), cv2.INTER_NEAREST)
    bank_edges = _resize_scalar(_label_edges(bank_small), cv2.INTER_NEAREST)
    uncolonized = _resize_scalar(1.0 - valid, cv2.INTER_NEAREST)

    # Generation bands are literal cell-division generations from the growth
    # history.  Their irregular branching is therefore not a contour field.
    generation_phase = _phase01(generation / 4.25)
    daughter_rims = _phase_band(generation_phase * TAU, .08 * TAU, .105 * TAU)
    mature_rims = _phase_band(generation_phase * TAU, .56 * TAU, .075 * TAU)
    lineage_walls = _dilate(clone_edges, 1)
    mutation_walls = _dilate(bank_edges, 2)
    active_growth = _f(_soft_gt(_n(birth), .74, .09) * daughter_rims)
    division_septa = _f(_edge(daughter_rims, 1) * (1.0 - lineage_walls))
    nutrient_channels = _f(_halo(lineage_walls, 4.0)
                           + .30 * _dilate(uncolonized, 2))
    inhibition_lacunae = _f(_dilate(uncolonized, 2))
    axial_splits = _f(_phase_band(_phase01(axes / 8.0 + generation / 7.0) * TAU,
                                  .27 * TAU, .105 * TAU)
                      * daughter_rims)

    masks = dict(
        parent_eden_lineages=parent,
        mutant_eden_lineages=mutant,
        daughter_generation_rims=daughter_rims,
        mature_generation_rims=mature_rims,
        clonal_lineage_walls=lineage_walls,
        mutation_takeover_walls=mutation_walls,
        active_growth_front=active_growth,
        division_septa=division_septa,
        nutrient_depletion_channels=nutrient_channels,
        inhibition_lacunae=inhibition_lacunae,
        inherited_axial_splits=axial_splits,
    )
    banks = dict(
        parent_eden_lineages="A", mutant_eden_lineages="B",
        daughter_generation_rims="B", mature_generation_rims="A",
        clonal_lineage_walls="A", mutation_takeover_walls="B",
        active_growth_front="B", division_septa="A",
        nutrient_depletion_channels="N", inhibition_lacunae="N",
        inherited_axial_splits="B",
    )
    spec = _literal_spec(
        masks,
        (("parent_eden_lineages", 178), ("mutant_eden_lineages", 38),
         ("daughter_generation_rims", 238), ("mature_generation_rims", 114),
         ("clonal_lineage_walls", 250), ("mutation_takeover_walls", 26),
         ("inherited_axial_splits", 206)),
        (("parent_eden_lineages", 88), ("mutant_eden_lineages", 182),
         ("daughter_generation_rims", 48), ("mature_generation_rims", 216),
         ("nutrient_depletion_channels", 242), ("active_growth_front", 32),
         ("inhibition_lacunae", 232)),
        (("parent_eden_lineages", 28), ("mutant_eden_lineages", 202),
         ("daughter_generation_rims", 246), ("mature_generation_rims", 82),
         ("mutation_takeover_walls", 230), ("division_septa", 156),
         ("active_growth_front", 252)),
    )
    tone = _n(generation) + .26 * lineage_walls + .22 * active_growth
    return _finish(masks, banks, tone, spec)


# ---------------------------------------------------------------------------
# Violet Garden: true diffusion-limited aggregation anatomy.


def w7_violet_garden() -> Grammar:
    aggregate = np.asarray(
        dla_aggregate(S, S, 0xA71D, res=256, n_walkers=24000,
                      max_steps=1050), np.float32
    )
    smooth = cv2.GaussianBlur(aggregate, (0, 0), 1.1)
    occupied = _soft_gt(aggregate, .47, .055)
    old_trunks = _soft_gt(aggregate, .67, .045)
    young_branches = _band(aggregate, .565, .105, .045)
    diffusion_sheaths = _band(aggregate, .365, .095, .045)
    nutrient_halos = _band(aggregate, .205, .075, .035)
    branch_cortex = _edge(occupied, 1)
    local_max = (smooth >= cv2.dilate(smooth, np.ones((9, 9), np.uint8)) - 1e-5)
    active_tips = _f(local_max.astype(np.float32) * _soft_gt(aggregate, .70, .055))
    active_tips = _dilate(active_tips, 2)
    lap = np.abs(cv2.Laplacian(smooth, cv2.CV_32F))
    fusion_necks = _f(_soft_gt(_n(lap), .71, .10) * young_branches)
    branch_age_rings = _phase_band(_phase01(aggregate * 7.0) * TAU,
                                   .13 * TAU, .085 * TAU) * occupied
    trapped_voids = _f(1.0 - _soft_gt(aggregate, .075, .035))
    dead_end_scars = _f(_edge(old_trunks, 1) * (1.0 - young_branches))
    spore_bulbs = _f(active_tips * (.42 + .58 * _halo(active_tips, 3.0)))

    masks = dict(
        old_aggregate_trunks=old_trunks,
        young_aggregate_branches=young_branches,
        diffusion_growth_sheaths=diffusion_sheaths,
        nutrient_capture_halos=nutrient_halos,
        branch_cortex_edges=branch_cortex,
        active_growth_tips=active_tips,
        branch_fusion_necks=fusion_necks,
        recorded_branch_age_rings=branch_age_rings,
        trapped_aggregation_voids=trapped_voids,
        dead_end_branch_scars=dead_end_scars,
        fruiting_spore_bulbs=spore_bulbs,
    )
    banks = dict(
        old_aggregate_trunks="A", young_aggregate_branches="B",
        diffusion_growth_sheaths="B", nutrient_capture_halos="A",
        branch_cortex_edges="A", active_growth_tips="B",
        branch_fusion_necks="B", recorded_branch_age_rings="A",
        trapped_aggregation_voids="N", dead_end_branch_scars="N",
        fruiting_spore_bulbs="B",
    )
    spec = _literal_spec(
        masks,
        (("old_aggregate_trunks", 224), ("young_aggregate_branches", 46),
         ("branch_cortex_edges", 246), ("active_growth_tips", 116),
         ("branch_fusion_necks", 28), ("dead_end_branch_scars", 82),
         ("fruiting_spore_bulbs", 174)),
        (("trapped_aggregation_voids", 238), ("old_aggregate_trunks", 68),
         ("young_aggregate_branches", 174), ("diffusion_growth_sheaths", 126),
         ("nutrient_capture_halos", 210), ("active_growth_tips", 34),
         ("dead_end_branch_scars", 154)),
        (("trapped_aggregation_voids", 18), ("old_aggregate_trunks", 76),
         ("young_aggregate_branches", 222), ("diffusion_growth_sheaths", 246),
         ("branch_fusion_necks", 162), ("active_growth_tips", 252),
         ("recorded_branch_age_rings", 122)),
    )
    tone = aggregate + .31 * branch_age_rings + .25 * active_tips
    return _finish(masks, banks, tone, spec)


# ---------------------------------------------------------------------------
# Lime Diatom: continuous dislocated silica diffraction field.


def w7_lime_diatom() -> Grammar:
    # Tilted valve coordinates.  The phase's line density is 2--5 work pixels
    # (8--20 at native 2048), while topological dislocations destroy any rail,
    # comb, fan or repeated-valve reading.
    xr = (U - .5) * .91 + (V - .5) * .414
    yr = -(U - .5) * .414 + (V - .5) * .91
    phase = TAU * (31.0 * yr + 2.8 * xr * xr - 1.7 * yr * yr
                   + 1.35 * np.sin(TAU * (1.13 * xr + .37 * yr))
                   + .72 * np.sin(TAU * (-.41 * xr + 1.71 * yr)))
    defects = ((-.39, -.31, 1), (-.23, -.12, -1), (-.08, .11, 1),
               (.09, .23, 1), (.22, .04, -1), (.35, -.18, 1),
               (.43, .29, -1), (-.31, .34, -1))
    core_field = np.zeros((S, S), np.float32)
    for dx, dy, charge in defects:
        rx, ry = xr - dx, yr - dy
        phase += charge * np.arctan2(ry, rx)
        radius2 = rx * rx + ry * ry
        core_field = np.maximum(core_field,
                                np.exp(-radius2 / (2.0 * .018 ** 2)).astype(np.float32))

    phase = np.asarray(phase, np.float32)
    crest = np.cos(phase)
    constructive = _soft_gt(crest, .42, .13)
    destructive = _soft_gt(-crest, .42, .13)
    silica_flanks = _band(crest, 0.0, .24, .10)

    # A single nonperiodic raphe threads the dislocations without becoming a
    # bilateral split.  It is subordinate to the full-frame phase field.
    raphe = np.zeros((S, S), np.float32)
    raphe_lips = np.zeros_like(raphe)
    xs = np.linspace(-24.0, 538.0, 300, dtype=np.float32)
    ys = (252.0 + 44.0 * np.sin(TAU * (xs / 552.0 + .09))
          + 17.0 * np.sin(TAU * (2.17 * xs / 552.0 + .27)))
    path = np.stack((xs, ys), axis=1)
    _curve(raphe_lips, path, 6)
    _curve(raphe, path, 2)

    fracture = np.zeros_like(raphe)
    chip = np.zeros_like(raphe)
    crack_paths = (
        ((-14, 88), (124, 102), (146, 310), (274, 530)),
        ((168, -18), (208, 98), (334, 218), (304, 544)),
        ((532, 52), (426, 172), (468, 332), (364, 544)),
        ((538, 344), (410, 350), (320, 454), (176, 540)),
    )
    for i, control in enumerate(crack_paths):
        crack = _bezier(*control, count=104)
        _curve(fracture, crack, 3 if i & 1 else 5)
        for k in (27, 58, 81):
            p = crack[k]
            tangent = crack[k + 2] - crack[k - 2]
            tangent /= np.linalg.norm(tangent) + 1e-6
            normal = np.asarray((-tangent[1], tangent[0]))
            _line(chip, p, p + normal * (7 + (i + k) % 7), 2)

    cut = _dilate(fracture, 2)
    constructive *= 1.0 - cut
    destructive *= 1.0 - cut
    silica_flanks *= 1.0 - cut
    repair = _f(_dilate(fracture, 5) - _dilate(fracture, 2)
                + .38 * _halo(chip, 2.8))
    phase_gradient = np.hypot(*np.gradient(phase))
    dislocation_crowns = _f(_dilate(core_field, 3)
                            * _soft_gt(_n(phase_gradient), .44, .16))
    longitudinal = _phase01(17.0 * xr + 2.2 * np.sin(TAU * yr))
    areolae = (_phase_band(longitudinal * TAU, .18 * TAU, .065 * TAU)
               * constructive)
    broken_striae_ends = _f(_dilate(fracture, 3)
                            * _dilate(np.maximum(constructive, destructive), 1))
    raphe_pressure_halo = _f(_halo(raphe_lips, 4.0)
                             * (.35 + .65 * silica_flanks))

    masks = dict(
        constructive_silica_striae=constructive,
        destructive_silica_striae=destructive,
        silica_stria_flanks=silica_flanks,
        central_raphe_slit=raphe,
        central_raphe_lips=raphe_lips,
        phase_dislocation_crowns=dislocation_crowns,
        costa_bound_areolae=areolae,
        through_valve_fractures=fracture,
        resilicified_repair_seams=repair,
        broken_stria_ends=broken_striae_ends,
        chipped_silica_edges=chip,
        raphe_pressure_halo=raphe_pressure_halo,
    )
    banks = dict(
        constructive_silica_striae="A", destructive_silica_striae="B",
        silica_stria_flanks="B", central_raphe_slit="N",
        central_raphe_lips="A", phase_dislocation_crowns="B",
        costa_bound_areolae="A", through_valve_fractures="N",
        resilicified_repair_seams="B", broken_stria_ends="A",
        chipped_silica_edges="N", raphe_pressure_halo="B",
    )
    spec = _literal_spec(
        masks,
        (("constructive_silica_striae", 224), ("destructive_silica_striae", 34),
         ("silica_stria_flanks", 128), ("central_raphe_lips", 246),
         ("phase_dislocation_crowns", 76), ("costa_bound_areolae", 174),
         ("through_valve_fractures", 22), ("broken_stria_ends", 208)),
        (("constructive_silica_striae", 54), ("destructive_silica_striae", 188),
         ("silica_stria_flanks", 112), ("central_raphe_slit", 242),
         ("phase_dislocation_crowns", 154), ("costa_bound_areolae", 214),
         ("resilicified_repair_seams", 38), ("chipped_silica_edges", 126)),
        (("constructive_silica_striae", 38), ("destructive_silica_striae", 224),
         ("silica_stria_flanks", 142), ("central_raphe_lips", 244),
         ("phase_dislocation_crowns", 196), ("costa_bound_areolae", 92),
         ("resilicified_repair_seams", 252), ("raphe_pressure_halo", 166)),
    )
    tone = _n(phase) + .32 * dislocation_crowns + .27 * repair
    return _finish(masks, banks, tone, spec)


BUILDERS: Mapping[str, Callable[[], Grammar]] = dict(w6.BUILDERS)
BUILDERS.update({
    "fpe_lime_culture": w7_lime_culture,
    "fpe_violet_garden": w7_violet_garden,
    "fpe_lime_diatom": w7_lime_diatom,
})
HUES = w6.HUES
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
