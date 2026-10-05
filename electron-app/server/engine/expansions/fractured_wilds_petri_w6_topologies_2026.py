# -*- coding: utf-8 -*-
"""WR-P6 topology replacements after the Petri W5 subset rejection.

W4 and W5 stay frozen as rejection evidence.  This isolated module replaces
only the three W5 experiments reviewed on 2026-08-24.  The replacements alter
their canvas-scale construction, not merely their density, phase, palette or
seed.  No random/noise layer is used and nothing here is production-wired.

SPB-WILDS 2026-08-24, WR-P6.  Candidate only; owner acceptance is not claimed.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np

from engine.expansions import fractured_wilds_petri_w5_topologies_2026 as w5


w4 = w5.w4
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


def _phase01(value):
    return np.mod(np.asarray(value, np.float32), 1.0)


# ---------------------------------------------------------------------------
# Lime Culture: full-plane competing clonal chronology.
#
# W5's recursive edge genealogies converged into one card-scale wedge/fan.
# This version instead records the first and second arrival of eleven unequal,
# anisotropic colonies.  Every fine mark is derived from that chronology:
# sector ownership, collision fronts, growth fronts, mutation wedges and
# lysis scars.  It therefore cannot be "fixed" or separated with noise.


def w6_lime_culture() -> Grammar:
    sites = np.asarray([
        (-74, 74), (84, -58), (244, -86), (432, -46), (584, 116),
        (572, 326), (430, 574), (254, 602), (70, 558), (-78, 386),
        (236, 276),
    ], np.float32)
    rotations = np.asarray((.22, 1.06, -.48, .61, 1.27, -.18,
                            .82, -.71, .37, 1.43, -.94), np.float32)
    stretch_x = np.asarray((.72, 1.18, .83, 1.26, .76, 1.11,
                            .88, 1.24, .79, 1.15, .91), np.float32)
    stretch_y = np.asarray((1.31, .78, 1.22, .74, 1.28, .82,
                            1.17, .76, 1.34, .86, 1.09), np.float32)
    offsets = np.asarray((6, -11, 18, -7, 13, -16, 3, 21, -13, 9, -4),
                         np.float32)
    genotypes = np.asarray((0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1), np.int8)

    first = np.full((S, S), np.inf, np.float32)
    second = np.full((S, S), np.inf, np.float32)
    labels = np.zeros((S, S), np.int16)
    all_arrivals = []
    for i, ((sx, sy), theta, ax, ay, offset) in enumerate(
            zip(sites, rotations, stretch_x, stretch_y, offsets)):
        dx, dy = X - sx, Y - sy
        c, s = np.cos(theta), np.sin(theta)
        xr, yr = c * dx + s * dy, -s * dx + c * dy
        radius = np.sqrt((xr / ax) ** 2 + (yr / ay) ** 2)
        polar = np.arctan2(yr / ay, xr / ax)
        # Deterministic front corrugation: it changes the actual arrival
        # boundary and is not a visual-noise overlay.
        arrival = (radius + offset
                   + (4.2 + i % 3) * np.sin((5 + i % 4) * polar + .071 * radius + i)
                   + 2.4 * np.sin(.113 * radius - (3 + i % 2) * polar + .43 * i))
        all_arrivals.append(arrival.astype(np.float32))
        take = arrival < first
        second = np.where(take, first, np.minimum(second, arrival))
        labels = np.where(take, i, labels)
        first = np.where(take, arrival, first)

    lineage = genotypes[labels]
    collision_gap = second - first
    interfaces = w4._label_edges(labels, 1)
    inhibition = _f(_dilate(interfaces, 5) - _dilate(interfaces, 2))

    # Broad sectors make the surface continuous.  Their internal chronology
    # is then broken into fine young/old fronts rather than left as flat cells.
    parent_sector = (lineage == 0).astype(np.float32)
    mutant_sector = (lineage == 1).astype(np.float32)
    chronology = _phase01((first + 1.8 * np.sin(.031 * X + .047 * Y)) / 15.0)
    young_fronts = _phase_band(chronology * TAU, .10 * TAU, .105 * TAU)
    old_fronts = _phase_band(chronology * TAU, .61 * TAU, .075 * TAU)
    young_fronts *= _f(1.0 - _dilate(interfaces, 1))
    old_fronts *= _f(1.0 - _dilate(interfaces, 1))
    division_septa = _edge(young_fronts, 1) * _f(1.0 - old_fronts)

    # Mutation sectors are literal wedges within three chosen lineages.  They
    # change both paint ownership and the material response of those sectors.
    mutation_phase = (np.sin(.019 * X + .011 * Y + .043 * first)
                      + .44 * np.sin(.007 * X - .027 * Y - .021 * first))
    mutation_fans = (_soft_gt(mutation_phase, .47, .16)
                     * mutant_sector * _f(.30 + .70 * young_fronts))

    # Lysis occurs where old fronts reach near-tie collision zones; this makes
    # short broken scars, not an unrelated speck/noise field.
    near_collision = _f((21.0 - collision_gap) / 11.0)
    lysis_scars = _edge(old_fronts * near_collision, 1)
    nutrient_channels = _f(_halo(interfaces, 4.4) + .42 * inhibition)
    active_collision_lips = _f(interfaces * (.38 + .62 * young_fronts)
                               + _edge(mutation_fans, 1))

    masks = dict(
        parent_clonal_sectors=parent_sector,
        mutant_clonal_sectors=mutant_sector,
        youngest_growth_fronts=young_fronts,
        mature_growth_fronts=old_fronts,
        division_septa=division_septa,
        sector_collision_interfaces=interfaces,
        nutrient_depletion_channels=nutrient_channels,
        mutation_fans=mutation_fans,
        inhibition_gaps=inhibition,
        collision_lysis_scars=lysis_scars,
        active_collision_lips=active_collision_lips,
    )
    banks = dict(
        parent_clonal_sectors="A", mutant_clonal_sectors="B",
        youngest_growth_fronts="B", mature_growth_fronts="A",
        division_septa="B", sector_collision_interfaces="A",
        nutrient_depletion_channels="N", mutation_fans="B",
        inhibition_gaps="N", collision_lysis_scars="N",
        active_collision_lips="B",
    )
    spec = _literal_spec(
        masks,
        (("parent_clonal_sectors", 178), ("mutant_clonal_sectors", 42),
         ("youngest_growth_fronts", 232), ("division_septa", 116),
         ("sector_collision_interfaces", 250), ("mutation_fans", 28),
         ("collision_lysis_scars", 86)),
        (("parent_clonal_sectors", 92), ("mutant_clonal_sectors", 174),
         ("mature_growth_fronts", 224), ("youngest_growth_fronts", 52),
         ("inhibition_gaps", 244), ("active_collision_lips", 118),
         ("collision_lysis_scars", 206)),
        (("parent_clonal_sectors", 28), ("mutant_clonal_sectors", 196),
         ("youngest_growth_fronts", 246), ("mature_growth_fronts", 84),
         ("mutation_fans", 222), ("nutrient_depletion_channels", 138),
         ("active_collision_lips", 252)),
    )
    tone = (_n(first) + .31 * young_fronts + .17 * old_fronts
            + .24 * near_collision)
    return _finish(masks, banks, tone, spec)


# ---------------------------------------------------------------------------
# Violet Garden: graph-derived living tube tissue.
#
# W5's transport graph is retained only as a causal skeleton.  Its large empty
# polygon cells are replaced by sheath, cortex and peristaltic layers computed
# from distance to that flow network.  The additions cannot float away from or
# be regenerated independently of the graph.


def w6_violet_garden() -> Grammar:
    base = w5.w5_violet_garden()
    old = {name: mask for name, mask, _owner in base.marks}
    high = old["high_flow_transport_veins"]
    low = old["low_flow_side_veins"]
    abandoned = old["abandoned_transport_links"]
    loops = old["anastomosis_loops"]
    pumps = old["multiway_pump_junctions"]
    spores = old["fruiting_spore_nodes"]
    scars = old["sealed_dead_end_scars"]
    droplets = old["nutrient_droplets"]

    skeleton = _f(np.maximum.reduce((high, low, loops)))
    inverse = (skeleton < .18).astype(np.uint8)
    distance = cv2.distanceTransform(inverse, cv2.DIST_L2, 5).astype(np.float32)
    living_tubes = _f((15.5 - distance) / 3.2)
    high_cytoplasm = _f(_dilate(high, 7) * living_tubes)
    side_cytoplasm = _f(_dilate(low, 5) * living_tubes)
    outer_membrane = _f(_edge(living_tubes, 1) + .45 * _halo(skeleton, 5.0))
    cortex = _f(((distance > 3.0) & (distance < 12.5)).astype(np.float32)
                * living_tubes)
    ring_phase = _phase01(distance / 4.75)
    peristaltic_rings = _phase_band(ring_phase * TAU, .16 * TAU, .105 * TAU)
    peristaltic_rings *= _f((distance < 14.0).astype(np.float32))
    streaming_cores = _f(_dilate(high, 2) + .54 * _dilate(low, 1))
    pump_chambers = _f(_dilate(pumps, 7) - .48 * _dilate(pumps, 2))
    dry_tubes = _f(_dilate(abandoned, 3) * (1.0 - living_tubes * .35))
    trapped_lacunae = _f(1.0 - _dilate(living_tubes, 1))
    anastomosis_stitches = _f(_dilate(loops, 2) + .36 * _edge(loops, 1))
    sealed_tips = _f(_dilate(scars, 2))
    spore_capsules = _f(_dilate(spores, 2) + .42 * droplets)

    masks = dict(
        high_flow_cytoplasm=high_cytoplasm,
        side_flow_cytoplasm=side_cytoplasm,
        streaming_transport_cores=streaming_cores,
        cortical_tube_tissue=cortex,
        outer_tube_membrane=outer_membrane,
        peristaltic_contraction_rings=peristaltic_rings,
        multiway_pump_chambers=pump_chambers,
        anastomosis_stitches=anastomosis_stitches,
        abandoned_dry_tubes=dry_tubes,
        sealed_transport_tips=sealed_tips,
        fruiting_spore_capsules=spore_capsules,
        trapped_garden_lacunae=trapped_lacunae,
    )
    banks = dict(
        high_flow_cytoplasm="A", side_flow_cytoplasm="B",
        streaming_transport_cores="A", cortical_tube_tissue="B",
        outer_tube_membrane="B", peristaltic_contraction_rings="A",
        multiway_pump_chambers="A", anastomosis_stitches="B",
        abandoned_dry_tubes="N", sealed_transport_tips="N",
        fruiting_spore_capsules="B", trapped_garden_lacunae="N",
    )
    spec = _literal_spec(
        masks,
        (("high_flow_cytoplasm", 216), ("side_flow_cytoplasm", 48),
         ("streaming_transport_cores", 246), ("cortical_tube_tissue", 126),
         ("multiway_pump_chambers", 184), ("abandoned_dry_tubes", 76),
         ("sealed_transport_tips", 154)),
        (("trapped_garden_lacunae", 238), ("high_flow_cytoplasm", 70),
         ("side_flow_cytoplasm", 166), ("peristaltic_contraction_rings", 36),
         ("abandoned_dry_tubes", 212), ("fruiting_spore_capsules", 112),
         ("outer_tube_membrane", 92)),
        (("trapped_garden_lacunae", 18), ("side_flow_cytoplasm", 218),
         ("outer_tube_membrane", 248), ("peristaltic_contraction_rings", 142),
         ("anastomosis_stitches", 232), ("fruiting_spore_capsules", 178),
         ("streaming_transport_cores", 82)),
    )
    tone = (_n(distance) + .42 * streaming_cores + .28 * peristaltic_rings
            + .18 * pump_chambers)
    return _finish(masks, banks, tone, spec)


# ---------------------------------------------------------------------------
# Lime Diatom: a single magnified fractured frustule surface.
#
# W5's 148 capsule stamps are gone.  The card is now a crop *inside* one valve:
# a nonperiodic raphe crosses the surface, forked costae grow out to both frame
# edges, areola pores follow those ribs, and fracture seams physically sever
# them.  There is no repeated valve outline or card-scale capsule.


def w6_lime_diatom() -> Grammar:
    upper_lamina = _blank(); lower_lamina = _blank()
    raphe_lips = _blank(); raphe_slit = _blank(); primary_costae = _blank()
    forked_costae = _blank(); fine_striae = _blank(); areola_pores = _blank()
    nodules = _blank(); fractures = _blank(); repair_seams = _blank()
    chipped_edges = _blank()

    def centre_y(x):
        z = np.asarray(x, np.float32) / S
        return (252.0 + 51.0 * np.sin(TAU * (.91 * z + .07))
                + 19.0 * np.sin(TAU * (2.43 * z + .31)))

    centre_field = centre_y(X)
    signed = Y - centre_field
    upper_lamina[:] = _f(.5 - signed / 3.4)
    lower_lamina[:] = _f(.5 + signed / 3.4)

    xs = np.arange(-28.0, 548.0, 2.0, dtype=np.float32)
    raphe_points = np.stack((xs, centre_y(xs)), axis=1)
    _curve(raphe_lips, raphe_points, 8)
    _curve(raphe_slit, raphe_points, 2)

    origins = []
    x = -18.0
    increments = (13.0, 17.0, 15.0, 21.0, 14.0, 19.0, 16.0)
    i = 0
    while x < 532:
        origins.append(x)
        x += increments[i % len(increments)]
        i += 1

    rib_paths = []
    for i, x0 in enumerate(origins):
        y0 = float(centre_y(x0))
        derivative = float(centre_y(x0 + 1.0) - centre_y(x0 - 1.0)) * .5
        tangent = np.asarray((1.0, derivative), np.float32)
        tangent /= np.linalg.norm(tangent) + 1.0e-6
        normal = np.asarray((-tangent[1], tangent[0]), np.float32)
        for side in (-1.0, 1.0):
            start = np.asarray((x0, y0), np.float32) + normal * side * 3.0
            lateral = (19.0 * np.sin(i * 1.17 + side)
                       + 8.0 * np.sin(i * .43 - 1.7 * side))
            reach = 300.0 + 34.0 * np.sin(i * .71 + side)
            c1 = start + normal * side * (48.0 + 9.0 * (i % 3)) + tangent * lateral
            c2 = start + normal * side * (166.0 + 13.0 * (i % 4)) - tangent * (1.7 * lateral)
            end = start + normal * side * reach + tangent * (62.0 * np.sin(i * .39 + side))
            path = _bezier(start, c1, c2, end, 52)
            rib_paths.append((i, side, path))
            _curve(primary_costae, path, 5 if (i + int(side)) % 4 else 7)
            # A subset truly bifurcates; the secondary branch shares the first
            # half of its parent's recorded trajectory.
            if (i + (side > 0)) % 3 == 1:
                junction = path[24]
                branch_end = end + tangent * side * (34.0 + 7.0 * (i % 5))
                branch = _bezier(junction,
                                 junction + normal * side * 31 + tangent * 10,
                                 end - normal * side * 36 + tangent * 22,
                                 branch_end, 34)
                _curve(forked_costae, branch, 3)
            # Fine transverse silica deposits are attached to, and locally
            # perpendicular to, each costa rather than scattered in the field.
            for k in (9, 18, 28, 39, 47):
                if k >= len(path):
                    continue
                p = path[k]
                t = path[min(len(path) - 1, k + 2)] - path[max(0, k - 2)]
                t /= np.linalg.norm(t) + 1.0e-6
                n = np.asarray((-t[1], t[0]), np.float32)
                span = 3.0 + ((i + k) % 4)
                _line(fine_striae, p - n * span, p + n * span, 2)
                if (i * 3 + k + int(side)) % 5 in (0, 1):
                    _circle(areola_pores, p + t * (2 + (i % 3)), 2, 2)

    # Unequal raphe nodules are not repeated valve icons; they interrupt the
    # one global slit at prescribed, visibly different points.
    for x0, axes, angle in ((42, (12, 6), -17), (226, (18, 8), 11),
                            (438, (10, 5), 26)):
        _ellipse(nodules, (x0, float(centre_y(x0))), axes, angle, 3)

    crack_paths = (
        ((-18, 112), (78, 148), (112, 232), (176, 548)),
        ((92, -16), (132, 126), (238, 198), (284, 536)),
        ((248, -20), (306, 104), (298, 330), (382, 548)),
        ((544, 42), (456, 150), (488, 298), (414, 542)),
        ((548, 286), (424, 310), (350, 422), (226, 548)),
    )
    for j, points in enumerate(crack_paths):
        path = _bezier(*points, count=88)
        _curve(fractures, path, 3 + (j % 2) * 2)
        for k in (19, 43, 67):
            p = path[k]
            tangent = path[k + 2] - path[k - 2]
            tangent /= np.linalg.norm(tangent) + 1.0e-6
            normal = np.asarray((-tangent[1], tangent[0]))
            if (j + k) % 2:
                _line(chipped_edges, p, p + normal * (8 + 2 * (j % 3)), 2)

    # Fractures actually sever the silica anatomy; repair seams occupy the
    # narrow material rim around the missing cut.
    cut = _dilate(fractures, 2)
    primary_costae[:] *= 1.0 - cut
    forked_costae[:] *= 1.0 - cut
    fine_striae[:] *= 1.0 - cut
    areola_pores[:] *= 1.0 - cut
    raphe_lips[:] *= 1.0 - cut
    raphe_slit[:] *= 1.0 - cut
    repair_seams[:] = _f(_dilate(fractures, 5) - _dilate(fractures, 2)
                         + .35 * _halo(chipped_edges, 3.0))

    masks = dict(
        upper_valve_lamina=upper_lamina,
        lower_valve_lamina=lower_lamina,
        central_raphe_lips=raphe_lips,
        central_raphe_slit=raphe_slit,
        load_bearing_costae=primary_costae,
        bifurcated_costae=forked_costae,
        transverse_silica_striae=fine_striae,
        costa_bound_areola_pores=areola_pores,
        asymmetric_central_nodules=nodules,
        through_valve_fractures=fractures,
        resilicified_repair_seams=repair_seams,
        chipped_fracture_edges=chipped_edges,
    )
    banks = dict(
        upper_valve_lamina="A", lower_valve_lamina="B",
        central_raphe_lips="B", central_raphe_slit="N",
        load_bearing_costae="A", bifurcated_costae="B",
        transverse_silica_striae="B", costa_bound_areola_pores="A",
        asymmetric_central_nodules="B", through_valve_fractures="N",
        resilicified_repair_seams="A", chipped_fracture_edges="N",
    )
    spec = _literal_spec(
        masks,
        (("upper_valve_lamina", 164), ("lower_valve_lamina", 38),
         ("load_bearing_costae", 238), ("bifurcated_costae", 112),
         ("costa_bound_areola_pores", 24), ("asymmetric_central_nodules", 196),
         ("through_valve_fractures", 72), ("resilicified_repair_seams", 252)),
        (("upper_valve_lamina", 88), ("lower_valve_lamina", 176),
         ("central_raphe_slit", 246), ("load_bearing_costae", 42),
         ("transverse_silica_striae", 132), ("costa_bound_areola_pores", 218),
         ("through_valve_fractures", 236), ("chipped_fracture_edges", 104)),
        (("upper_valve_lamina", 34), ("lower_valve_lamina", 194),
         ("central_raphe_lips", 242), ("bifurcated_costae", 216),
         ("transverse_silica_striae", 154), ("asymmetric_central_nodules", 94),
         ("resilicified_repair_seams", 250), ("chipped_fracture_edges", 126)),
    )
    tone = (_n(np.abs(signed)) + .34 * primary_costae + .25 * fine_striae
            + .31 * repair_seams)
    return _finish(masks, banks, tone, spec)


BUILDERS: Mapping[str, Callable[[], Grammar]] = dict(w5.BUILDERS)
BUILDERS.update({
    "fpe_lime_culture": w6_lime_culture,
    "fpe_violet_garden": w6_violet_garden,
    "fpe_lime_diatom": w6_lime_diatom,
})
HUES = w5.HUES
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
