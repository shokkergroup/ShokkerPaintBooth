# -*- coding: utf-8 -*-
"""WR-P8 replacements after the physical-process W7 board was rejected.

Culture now uses a continuous deterministic chemotactic swarm, Garden crops
inside one recorded DLA aggregate, and Diatom uses a complex multi-wave silica
field whose zeros create genuine topological phase dislocations.  No W6/W7
dominant carrier is retained and no decorative random/noise layer is present.

SPB-WILDS 2026-08-24, WR-P8.  Isolated candidate; not production-wired and no
owner acceptance is claimed.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np

from engine.expansions import fractured_wilds_petri_w7_topologies_2026 as w7


w6, w5, w4 = w7.w6, w7.w5, w7.w4
S, X, Y, U, V, TAU = w4.S, w4.X, w4.Y, w4.U, w4.V, w4.TAU
Grammar = w4.Grammar
_f, _n = w4._f, w4._n
_soft_gt, _band, _phase_band = w4._soft_gt, w4._band, w4._phase_band
_edge, _dilate, _erode, _halo = w4._edge, w4._dilate, w4._erode, w4._halo
_curve, _line, _circle, _ellipse, _bezier = (
    w4._curve, w4._line, w4._circle, w4._ellipse, w4._bezier
)
_literal_spec, _finish = w4._literal_spec, w4._finish
_sites = w4._sites


def _blank():
    return np.zeros((S, S), np.float32)


def _phase01(value):
    return np.mod(np.asarray(value, np.float32), 1.0)


# ---------------------------------------------------------------------------
# Lime Culture: continuous chemotactic swarm.


def _chemotactic_velocity(points):
    p = np.asarray(points, np.float32)
    x, y = p[:, 0], p[:, 1]
    vx = (1.05 + .42 * np.sin(y * .018) - .31 * np.cos((x + y) * .011)
          + .20 * np.sin((2 * x - y) * .007))
    vy = (.58 * np.sin(x * .015 + .7) + .34 * np.cos(y * .021 - .4)
          - .22 * np.sin((x + 2 * y) * .009))
    # Off-canvas chemical reservoirs bend every trajectory coherently without
    # introducing visible hubs.  Internal repellents make wakes, not stamps.
    reservoirs = ((-170.0, 72.0, 1.25), (686.0, 146.0, 1.08),
                  (-132.0, 474.0, .94), (704.0, 588.0, 1.18))
    repellents = ((124.0, 104.0, -.62), (372.0, 86.0, -.48),
                  (214.0, 328.0, -.71), (462.0, 392.0, -.57),
                  (84.0, 448.0, -.44))
    for sx, sy, strength in reservoirs + repellents:
        dx, dy = sx - x, sy - y
        r2 = dx * dx + dy * dy + 1550.0
        vx += strength * 1550.0 * dx / r2
        vy += strength * 1550.0 * dy / r2
        if strength < 0:
            # Chiral wall-following around inhibitors makes long deflected
            # wakes; it is part of the motion law, never a texture overlay.
            vx += -.34 * strength * 1550.0 * dy / r2
            vy += .34 * strength * 1550.0 * dx / r2
    speed = np.hypot(vx, vy) + 1.0e-6
    return np.stack((vx / speed, vy / speed), axis=1).astype(np.float32)


def w8_lime_culture() -> Grammar:
    parent_tracks = _blank(); mutant_tracks = _blank()
    leading_fronts = _blank(); trailing_stalks = _blank(); division_forks = _blank()
    adhesion_plaques = _blank(); inhibitor_wakes = _blank(); conjugation = _blank()

    starts = _sites(760, phase=137, margin=-18)
    genotype = (((starts[:, 0] * .013 + starts[:, 1] * .019
                  + np.sin(starts[:, 0] * .031)) % 2.0) > 1.0)
    endpoints = []
    for i, start in enumerate(starts):
        path = [start.copy()]
        p = start.copy()[None, :]
        for step in range(42):
            direction = _chemotactic_velocity(p)[0]
            # A lineage-specific orthogonal response produces visible A/B
            # braiding while both still obey the same chemical landscape.
            if genotype[i]:
                direction = direction + .13 * np.asarray((-direction[1], direction[0]))
                direction /= np.linalg.norm(direction) + 1.0e-6
            p[0] += direction * (2.35 + .18 * np.sin(i * .37 + step * .41))
            if not (-28 <= p[0, 0] <= 540 and -28 <= p[0, 1] <= 540):
                break
            path.append(p[0].copy())
        if len(path) < 4:
            continue
        path = np.asarray(path, np.float32)
        body = mutant_tracks if genotype[i] else parent_tracks
        _curve(body, path, 2 if i % 5 else 3)
        split = max(2, len(path) * 2 // 3)
        _curve(trailing_stalks, path[:split], 2)
        _curve(leading_fronts, path[split - 1:], 3)
        endpoints.append((path[-1].copy(), bool(genotype[i])))

        if i % 11 in (2, 7) and len(path) > 18:
            k = 10 + (i * 7) % (len(path) - 12)
            tangent = path[k + 1] - path[k - 1]
            tangent /= np.linalg.norm(tangent) + 1.0e-6
            normal = np.asarray((-tangent[1], tangent[0]))
            branch_end = path[k] + tangent * (11 + i % 7) + normal * (7 if i & 1 else -7)
            branch = _bezier(path[k], path[k] + tangent * 5,
                             branch_end - normal * 3, branch_end, 18)
            _curve(division_forks, branch, 2)
        if i % 17 == 4:
            _ellipse(adhesion_plaques, path[-1], (4 + i % 3, 2 + (i // 3) % 2),
                     i * 19, 2)

    parent_sheath = _f(_halo(parent_tracks, 3.2) + .36 * _dilate(parent_tracks, 2))
    mutant_sheath = _f(_halo(mutant_tracks, 3.2) + .36 * _dilate(mutant_tracks, 2))
    collision_braids = _f(_dilate(parent_tracks, 2) * _dilate(mutant_tracks, 2))
    density = cv2.GaussianBlur(np.maximum(parent_tracks, mutant_tracks), (0, 0), 6.0)
    swarm_pressure = _band(_n(density), .55, .19, .10)

    # Conjugation only occurs where recorded opposite-lineage endpoints meet.
    for i in range(0, len(endpoints), 23):
        a, ga = endpoints[i]
        candidates = [(np.linalg.norm(a - b), b) for b, gb in endpoints
                      if gb != ga and 7.0 < np.linalg.norm(a - b) < 24.0]
        if candidates:
            _distance, b = min(candidates, key=lambda row: row[0])
            _curve(conjugation, _bezier(a, a + (3, -4), b + (-3, 4), b, 16), 2)

    # Wake material is the low-density rim behind the same moving swarm.
    inhibitor_wakes[:] = _f(_halo(np.maximum(parent_sheath, mutant_sheath), 5.2)
                             * (1.0 - collision_braids))
    culture_medium = _f(1.0 - _dilate(np.maximum(parent_sheath, mutant_sheath), 1))

    masks = dict(
        parent_chemotactic_tracks=parent_tracks,
        mutant_chemotactic_tracks=mutant_tracks,
        parent_mucous_sheaths=parent_sheath,
        mutant_mucous_sheaths=mutant_sheath,
        active_leading_fronts=leading_fronts,
        trailing_transport_stalks=trailing_stalks,
        daughter_division_forks=division_forks,
        opposite_lineage_collision_braids=collision_braids,
        endpoint_adhesion_plaques=adhesion_plaques,
        conjugation_bridges=conjugation,
        chemotactic_inhibitor_wakes=inhibitor_wakes,
        swarm_pressure_ridges=swarm_pressure,
        depleted_culture_medium=culture_medium,
    )
    banks = dict(
        parent_chemotactic_tracks="A", mutant_chemotactic_tracks="B",
        parent_mucous_sheaths="A", mutant_mucous_sheaths="B",
        active_leading_fronts="B", trailing_transport_stalks="A",
        daughter_division_forks="B", opposite_lineage_collision_braids="A",
        endpoint_adhesion_plaques="B", conjugation_bridges="B",
        chemotactic_inhibitor_wakes="N", swarm_pressure_ridges="A",
        depleted_culture_medium="N",
    )
    spec = _literal_spec(
        masks,
        (("parent_chemotactic_tracks", 222), ("mutant_chemotactic_tracks", 36),
         ("parent_mucous_sheaths", 152), ("mutant_mucous_sheaths", 82),
         ("active_leading_fronts", 246), ("daughter_division_forks", 116),
         ("opposite_lineage_collision_braids", 252),
         ("endpoint_adhesion_plaques", 24)),
        (("depleted_culture_medium", 234), ("parent_chemotactic_tracks", 62),
         ("mutant_chemotactic_tracks", 184), ("active_leading_fronts", 34),
         ("trailing_transport_stalks", 132), ("conjugation_bridges", 96),
         ("chemotactic_inhibitor_wakes", 212), ("swarm_pressure_ridges", 158)),
        (("depleted_culture_medium", 18), ("parent_chemotactic_tracks", 72),
         ("mutant_chemotactic_tracks", 224), ("mutant_mucous_sheaths", 246),
         ("active_leading_fronts", 198), ("conjugation_bridges", 252),
         ("opposite_lineage_collision_braids", 142),
         ("endpoint_adhesion_plaques", 104)),
    )
    tone = _n(density) + .31 * leading_fronts + .24 * collision_braids
    return _finish(masks, banks, tone, spec)


# ---------------------------------------------------------------------------
# Violet Garden: crop inside one real DLA aggregate.


def _largest_aggregate_crop(field):
    f = np.asarray(field, np.float32)
    binary = (f > .44).astype(np.uint8)
    count, labels, stats, _centres = cv2.connectedComponentsWithStats(binary, 8)
    if count <= 1:
        return f
    index = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, _area = stats[index]
    # Crop *inside* the aggregate's recorded bounding box so branches, voids
    # and age bands cross every card edge instead of floating as a specimen.
    inset_x = int(w * .10)
    inset_y = int(h * .10)
    x0, x1 = max(0, x + inset_x), min(f.shape[1], x + w - inset_x)
    y0, y1 = max(0, y + inset_y), min(f.shape[0], y + h - inset_y)
    crop = f[y0:y1, x0:x1]
    if crop.size < 64:
        crop = f[y:y + h, x:x + w]
    return cv2.resize(crop, (S, S), interpolation=cv2.INTER_CUBIC).astype(np.float32)


def w8_violet_garden() -> Grammar:
    raw = w7.dla_aggregate(S, S, 0xA71D, res=320, n_walkers=36000,
                           max_steps=1250)
    aggregate = _n(_largest_aggregate_crop(raw))
    smooth = cv2.GaussianBlur(aggregate, (0, 0), .85)
    occupied = _soft_gt(aggregate, .39, .055)
    old_trunks = _soft_gt(aggregate, .69, .045)
    young_branches = _band(aggregate, .565, .115, .045)
    diffusion_sheaths = _band(aggregate, .335, .095, .04)
    nutrient_halos = _band(aggregate, .19, .065, .03)
    branch_cortex = _edge(occupied, 1)
    local_max = (smooth >= cv2.dilate(smooth, np.ones((9, 9), np.uint8)) - 1e-5)
    active_tips = _dilate(_f(local_max.astype(np.float32)
                             * _soft_gt(aggregate, .67, .05)), 2)
    lap = np.abs(cv2.Laplacian(smooth, cv2.CV_32F))
    fusion_necks = _f(_soft_gt(_n(lap), .70, .10) * young_branches)
    branch_age_rings = (_phase_band(_phase01(aggregate * 6.5) * TAU,
                                    .16 * TAU, .075 * TAU) * occupied)
    trapped_voids = _f(1.0 - _soft_gt(aggregate, .09, .035))
    dead_end_scars = _f(_edge(old_trunks, 1) * (1.0 - young_branches))
    spore_bulbs = _f(active_tips * (.46 + .54 * _halo(active_tips, 2.6)))

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
# Lime Diatom: multi-wave complex phase with genuine zeros/dislocations.


def w8_lime_diatom() -> Grammar:
    x, y = (U - .5).astype(np.float32), (V - .5).astype(np.float32)
    waves = (
        (0.00, 13.0, 1.00, .00, .00),
        (0.61, 16.7, .82, .47, 1.20),
        (1.37, 11.9, .71, -.39, 2.10),
        (2.18, 18.3, .63, .61, .70),
        (2.77, 14.4, .54, -.73, 2.70),
        (1.86, 20.1, .43, .84, 1.75),
        (.93, 9.7, .37, -.56, 3.10),
    )
    z = np.zeros((S, S), np.complex64)
    for angle, frequency, weight, chirp, phase0 in waves:
        c, s = np.cos(angle), np.sin(angle)
        longitudinal = x * c + y * s
        transverse = -x * s + y * c
        phase = (TAU * frequency * longitudinal
                 + TAU * chirp * (longitudinal * longitudinal
                                   - .72 * transverse * transverse)
                 + phase0)
        z += np.complex64(weight) * np.exp(1j * phase).astype(np.complex64)
    amplitude = _n(np.abs(z))
    phase = np.angle(z).astype(np.float32)

    constructive = _phase_band(phase, 0.0, .48)
    destructive = _phase_band(phase, np.pi, .48)
    silica_flanks = _f(_phase_band(phase, .5 * np.pi, .34)
                       + _phase_band(phase, -.5 * np.pi, .34))
    dislocation_cores = _f((.31 - amplitude) / .13)
    dislocation_crowns = _f(_dilate(dislocation_cores, 3)
                            - _dilate(dislocation_cores, 1))
    caustic_costae = _soft_gt(amplitude, .73, .10)
    gradient = np.hypot(*np.gradient(phase))
    broken_phase_seams = _f(_soft_gt(_n(gradient), .74, .10)
                            * (1.0 - dislocation_cores))

    # The raphe is a discontinuous slit selected from the field's own low-
    # amplitude branch cut; no long independent line is drawn over the phase.
    raphe_curve = y - (.08 * np.sin(TAU * (1.15 * x + .12))
                       + .035 * np.sin(TAU * (3.1 * x - .21)))
    raphe_gate = _f((.010 - np.abs(raphe_curve)) / .005)
    central_raphe = _f(raphe_gate * _soft_gt(.58 - amplitude, .12, .10))
    raphe_lips = _f(_dilate(central_raphe, 3) - _dilate(central_raphe, 1))

    longitudinal = _phase01(19.0 * x + 2.4 * y + .65 * amplitude)
    areolae = (_phase_band(longitudinal * TAU, .17 * TAU, .07 * TAU)
               * caustic_costae)
    fracture_genealogy = _f(broken_phase_seams * _dilate(dislocation_crowns, 8))
    resilicified_seams = _f(_halo(fracture_genealogy, 3.1)
                            + .34 * dislocation_crowns)
    terminal_pores = _f(_dilate(dislocation_cores, 1)
                        * (.34 + .66 * _phase_band(longitudinal * TAU,
                                                   .63 * TAU, .09 * TAU)))
    optical_saddles = _band(amplitude, .52, .10, .05)

    masks = dict(
        constructive_silica_striae=constructive,
        destructive_silica_striae=destructive,
        silica_phase_flanks=silica_flanks,
        amplitude_caustic_costae=caustic_costae,
        phase_dislocation_cores=dislocation_cores,
        phase_dislocation_crowns=dislocation_crowns,
        field_selected_central_raphe=central_raphe,
        central_raphe_lips=raphe_lips,
        costa_bound_areolae=areolae,
        dislocation_fracture_genealogy=fracture_genealogy,
        resilicified_phase_seams=resilicified_seams,
        terminal_dislocation_pores=terminal_pores,
        optical_silica_saddles=optical_saddles,
    )
    banks = dict(
        constructive_silica_striae="A", destructive_silica_striae="B",
        silica_phase_flanks="B", amplitude_caustic_costae="A",
        phase_dislocation_cores="N", phase_dislocation_crowns="B",
        field_selected_central_raphe="N", central_raphe_lips="A",
        costa_bound_areolae="A", dislocation_fracture_genealogy="N",
        resilicified_phase_seams="B", terminal_dislocation_pores="A",
        optical_silica_saddles="B",
    )
    spec = _literal_spec(
        masks,
        (("constructive_silica_striae", 218), ("destructive_silica_striae", 34),
         ("silica_phase_flanks", 118), ("amplitude_caustic_costae", 246),
         ("phase_dislocation_cores", 18), ("phase_dislocation_crowns", 174),
         ("costa_bound_areolae", 82), ("resilicified_phase_seams", 232)),
        (("constructive_silica_striae", 52), ("destructive_silica_striae", 188),
         ("silica_phase_flanks", 126), ("amplitude_caustic_costae", 38),
         ("phase_dislocation_cores", 242), ("central_raphe_lips", 96),
         ("terminal_dislocation_pores", 214), ("optical_silica_saddles", 154)),
        (("constructive_silica_striae", 36), ("destructive_silica_striae", 224),
         ("silica_phase_flanks", 146), ("phase_dislocation_crowns", 242),
         ("central_raphe_lips", 196), ("costa_bound_areolae", 88),
         ("resilicified_phase_seams", 252), ("optical_silica_saddles", 174)),
    )
    tone = amplitude + .30 * dislocation_crowns + .24 * caustic_costae
    return _finish(masks, banks, tone, spec)


BUILDERS: Mapping[str, Callable[[], Grammar]] = dict(w7.BUILDERS)
BUILDERS.update({
    "fpe_lime_culture": w8_lime_culture,
    "fpe_violet_garden": w8_violet_garden,
    "fpe_lime_diatom": w8_lime_diatom,
})
HUES = w7.HUES
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
