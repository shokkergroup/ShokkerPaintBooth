# -*- coding: utf-8 -*-
"""Owner-rejection rebuild for FRACTURED BLOOM and FRACTURED PETRI.

SPB-WILDS-REJECTION 2026-08-24, WR-2.  Owner verdict: "the biggest
cardinal sin PERIOD of this app - LAZY" and "do NOT just put random noise in
the patterns to separate the way they look."  The rejected release routed all
forty entries through ``fractured_wilds_microkit_2026._signature_fields``.
The frozen paint audit found twenty exact Bloom <-> Petri routing pairs and
measured the finish-specific generator at only three percent of visible
structure.

This override removes that architecture.  Each ID's original, separately
authored mathematical generator is again the dominant paint and material
topology.  Source-attached fills, crests, troughs, contours, junctions,
orientation marks, and saddle/curvature marks provide the fine material
relief.  No random grain, random fleck layer, shared glyph scatter, global
role router, or equal-population rank quantizer is used.

The work canvas is 512 square.  The restored Bloom/Petri engines were already
authored around 2-8 work-pixel primitives (8-32 px at native 2048); this
module never enlarges them.  Fifteen-color banks (three structural hue
families x five value shades) and explicit eight-shade M/R/Cc ladders keep
the finish rich without allowing palette changes to impersonate topology.

This module deliberately does *not* claim owner acceptance.  It is installed
only after palette-free paint, individual channel, angle-opponent, native
performance, and M7 evidence have been regenerated and inspected.
"""
from __future__ import annotations

import colorsys
import itertools
from functools import lru_cache
from typing import Mapping

import cv2
import numpy as np

from engine.expansions import fractured_bloom_2026 as _bloom
from engine.expansions import fractured_petri_2026 as _petri
from engine.paint_v2 import exotic_engines_2026 as _exotic


_DESIGN = 512
_METAL_TIERS = np.asarray([0, 36, 72, 108, 144, 180, 220, 255], np.uint8)
_ROUGH_TIERS = np.asarray([12, 38, 66, 94, 122, 150, 180, 214], np.uint8)
_COAT_TIERS = np.asarray([16, 46, 78, 110, 142, 174, 208, 242], np.uint8)
_FIXED_THRESHOLDS = np.asarray([0.06, 0.15, 0.27, 0.41, 0.56, 0.71, 0.85], np.float32)


# These are literal parts of each named construction, not metric-padding
# labels.  The source engines draw them as one causal system; the derivative
# masks below expose their different material ownership.
_SEMANTIC_MARKS = {
    "fbl_magenta_whorl": ("seed cups", "clockwise parastichies", "counter-parastichies", "ligules", "bract hooks", "vascular arcs", "broken cups"),
    "fbl_leafvine_drape": ("climbing stems", "trellis crossings", "node collars", "leaf pairs", "tendril loops", "pods", "underpasses"),
    "fbl_butter_pollen": ("exine bodies", "echinate crowns", "colpi", "germ pores", "reticulation", "cracked shells", "adhesion bridges"),
    "fbl_pink_rose": ("petal shells", "curled margins", "midribs", "sepals", "stamen arcs", "dew cups", "inter-petal slits"),
    "fbl_coral_cluster": ("branch trunks", "fork tips", "axial mouths", "radial septa", "calices", "growth rings", "living polyps"),
    "fbl_butter_mosaic": ("plate faces", "grout seams", "floret stamps", "ray petals", "button centers", "bevels", "missing-tile scars"),
    "fbl_pink_pollen": ("pollen bodies", "impact fronts", "wake tails", "adhesion chains", "rebound arcs", "lee gaps", "broken exines"),
    "fbl_white_whorl": ("gardenia cups", "overlap lips", "petal cushions", "central throats", "fold saddles", "dew rims", "torn margins"),
    "fbl_coral_stamen": ("filament fans", "bilobed anthers", "pollen sacs", "dehiscence seams", "connective bars", "stigma curls", "base bracts"),
    "fbl_lilac_rose": ("reaction walls", "petal bays", "curl tips", "branch saddles", "closed chambers", "rupture gaps", "rim fronts"),
    "fbl_coral_vine": ("primary stems", "secondary veins", "Y nodes", "bud cups", "thorn tips", "leaf sockets", "anastomosis bridges"),
    "fbl_lilac_stamen": ("ray bundles", "anther beads", "core discs", "cross braces", "missing rays", "halo rings", "lattice bridges"),
    "fbl_magenta_mosaic": ("four-lobe florets", "cell walls", "button eyes", "petal midribs", "corner notches", "overlap lips", "broken cells"),
    "fbl_leaf_whorl": ("leaflet pleats", "central rachides", "chevron ribs", "serrated margins", "node bands", "over-under seams", "tip hooks"),
    "fbl_white_pollen": ("windward grains", "impact flats", "wake deposits", "eddy chains", "clear shadows", "rebound shells", "adhesion films"),
    "fbl_pink_stamen": ("filament combs", "anther tips", "base rails", "cross ties", "bent teeth", "missing sockets", "pollen beads"),
    "fbl_blush_rose": ("shingled petals", "fan ribs", "overlap scallops", "tip notches", "basal pockets", "curl lips", "vein forks"),
    "fbl_lilac_vine": ("raceme strands", "pea blossoms", "node collars", "tendril knots", "leaf pairs", "pods", "over-under crossings"),
    "fbl_butter_whorl": ("pinwheel arms", "spiral grooves", "button cores", "petal rims", "interlock notches", "curl tips", "broken arms"),
    "fbl_magenta_pollen": ("porate grains", "germ pores", "exine mesh", "annular rims", "contact flats", "crack cuts", "pollen bridges"),
    "fpe_magenta_bloom": ("colony domes", "daughter buds", "division necks", "wet rims", "contact saddles", "rupture scars", "satellite cells"),
    "fpe_cyan_membrane": ("bilayer walls", "channel gates", "vesicle buds", "protein rafts", "fusion necks", "pore rings", "broken ends"),
    "fpe_lime_culture": ("clonal sectors", "growth fronts", "mutation fans", "nutrient channels", "division septa", "satellites", "inhibition gaps"),
    "fpe_amber_agar": ("dry plates", "primary cracks", "secondary crazing", "lifted lips", "moist islands", "healed bridges", "junction pits"),
    "fpe_violet_garden": ("branch trunks", "active tips", "side branches", "trapped voids", "age bands", "spore bulbs", "bridge scars"),
    "fpe_lime_diatom": ("boat valves", "raphe slits", "bilateral striae", "costae", "central nodules", "terminal pores", "girdle bands"),
    "fpe_magenta_mosaic": ("tissue plates", "cell membranes", "chromatin bodies", "nuclear rims", "division furrows", "junction nodes", "torn cells"),
    "fpe_cyan_spineball": ("silica shells", "spine roots", "radial spines", "pore fields", "inner cages", "broken sockets", "aperture collars"),
    "fpe_amber_moldring": ("colony cores", "growth rings", "fuzzy fronts", "sector wedges", "inhibition halos", "spore rims", "collision scars"),
    "fpe_violet_chains": ("yeast bodies", "bud necks", "mother scars", "closed loops", "branch nodes", "terminal buds", "ruptured links"),
    "fpe_cyan_colony": ("mother colonies", "daughter satellites", "radial channels", "division fronts", "void halos", "bridge necks", "shed cells"),
    "fpe_lime_mold": ("hyphal mats", "spore heads", "conidia chains", "clear lanes", "branch forks", "fruiting rims", "dead zones"),
    "fpe_amber_diatom": ("needle valves", "raphe grooves", "transverse striae", "terminal nodules", "girdle seams", "crossed felts", "broken tips"),
    "fpe_magenta_radiolaria": ("shell panels", "polygon pores", "radial struts", "inner cages", "spine roots", "tapered spines", "aperture collars"),
    "fpe_cyan_mold": ("primary hyphae", "side branches", "anastomoses", "conidia beads", "active tips", "empty lacunae", "dead-end scars"),
    "fpe_amber_plankton": ("segmented ribbons", "crossing bands", "hinge joints", "cilia combs", "eye spots", "wake curls", "broken segments"),
    "fpe_violet_membrane": ("saddle patches", "connected channels", "neck rings", "protein rods", "transmembrane pores", "cleavage domains", "vesicle buds"),
    "fpe_lime_chains": ("cocci beads", "division septa", "chain bends", "branch forks", "contact flats", "terminal cells", "broken links"),
    "fpe_violet_frustule": ("centric valves", "central rosettes", "areola rows", "marginal spines", "ring bands", "rimoportula pores", "broken sectors"),
    "fpe_magenta_plankton": ("advected specks", "stream ribbons", "vortex eyes", "paired wakes", "orbit chains", "shear gaps", "collision knots"),
}


# Different source topologies want different aspects exposed.  This selection
# changes which source-attached masks lead paint; it never replaces the source
# with a universal texture.
_MODE_BY_ID = {
    "fbl_magenta_whorl": "radial", "fbl_leafvine_drape": "woven",
    "fbl_butter_pollen": "nodes", "fbl_pink_rose": "flow",
    "fbl_coral_cluster": "cells", "fbl_butter_mosaic": "facets",
    "fbl_pink_pollen": "flow", "fbl_white_whorl": "relief",
    "fbl_coral_stamen": "filament", "fbl_lilac_rose": "labyrinth",
    "fbl_coral_vine": "filament", "fbl_lilac_stamen": "radial",
    "fbl_magenta_mosaic": "facets", "fbl_leaf_whorl": "woven",
    "fbl_white_pollen": "nodes", "fbl_pink_stamen": "filament",
    "fbl_blush_rose": "relief", "fbl_lilac_vine": "woven",
    "fbl_butter_whorl": "radial", "fbl_magenta_pollen": "cells",
    "fpe_magenta_bloom": "relief", "fpe_cyan_membrane": "labyrinth",
    "fpe_lime_culture": "fronts", "fpe_amber_agar": "fracture",
    "fpe_violet_garden": "filament", "fpe_lime_diatom": "woven",
    "fpe_magenta_mosaic": "facets", "fpe_cyan_spineball": "radial",
    "fpe_amber_moldring": "bands", "fpe_violet_chains": "filament",
    "fpe_cyan_colony": "cells", "fpe_lime_mold": "fronts",
    "fpe_amber_diatom": "woven", "fpe_magenta_radiolaria": "facets",
    "fpe_cyan_mold": "filament", "fpe_amber_plankton": "flow",
    "fpe_violet_membrane": "saddles", "fpe_lime_chains": "filament",
    "fpe_violet_frustule": "radial", "fpe_magenta_plankton": "flow",
}


# WR-2 owner-eye iteration.  Merely restoring the old Bloom/Petri generators
# was still insufficient: a hue-null contact showed too many fine paves with
# the same visual rhythm.  These forty non-repeating assignments select forty
# unrelated recent math mechanisms.  The repeat count only brings the source
# mechanism into the mandated fine car scale; it is not used as identity and
# no two finishes share a source.  Candidate board:
# ``_wilds_rejection_work/exotic_assignments/assignment_hue_null_contact.png``.
_EXOTIC_SOURCE_BY_ID = {
    "fbl_magenta_whorl": ("bz_spirals", 4),
    "fbl_leafvine_drape": ("thorn_bramble", 3),
    "fbl_butter_pollen": ("ford_circles", 5),
    "fbl_pink_rose": ("rhodonea_field", 4),
    "fbl_coral_cluster": ("dla_aggregate", 3),
    "fbl_butter_mosaic": ("hat_monotile", 3),
    "fbl_pink_pollen": ("potential_flow_cylinders", 5),
    "fbl_white_whorl": ("rose_window", 12),
    "fbl_coral_stamen": ("cardioid_caustic", 10),
    "fbl_lilac_rose": ("dark_damask", 5),
    "fbl_coral_vine": ("gosper_flowsnake", 4),
    "fbl_lilac_stamen": ("reactor_lattice", 4),
    "fbl_magenta_mosaic": ("spectre_monotile", 3),
    "fbl_leaf_whorl": ("clelie_spiral", 12),
    "fbl_white_pollen": ("ferrofluid_spikes", 3),
    "fbl_pink_stamen": ("fourier_epicycle", 12),
    "fbl_blush_rose": ("quatrefoil_tess", 4),
    "fbl_lilac_vine": ("epitrochoid_weave", 6),
    "fbl_butter_whorl": ("spirograph_lattice", 5),
    "fbl_magenta_pollen": ("wallpaper_p6m", 3),
    "fpe_magenta_bloom": ("hodgepodge", 2),
    "fpe_cyan_membrane": ("gray_scott_uskate", 2),
    "fpe_lime_culture": ("eden_growth", 3),
    "fpe_amber_agar": ("crack_network", 2),
    "fpe_violet_garden": ("pythagoras_tree", 5),
    "fpe_lime_diatom": ("diffraction_grating", 2),
    "fpe_magenta_mosaic": ("ammann_beenker", 3),
    "fpe_cyan_spineball": ("hyperbolic_pqr", 8),
    "fpe_amber_moldring": ("liesegang_rings", 6),
    "fpe_violet_chains": ("neural_ca_worms", 2),
    "fpe_cyan_colony": ("lenia", 2),
    "fpe_lime_mold": ("rust_bloom", 3),
    "fpe_amber_diatom": ("scratch_striation", 2),
    "fpe_magenta_radiolaria": ("superformula_field", 5),
    "fpe_cyan_mold": ("tracery_web", 3),
    "fpe_amber_plankton": ("curl_streaklines", 3),
    "fpe_violet_membrane": ("bubble_lattice", 3),
    "fpe_lime_chains": ("steiner_chain", 6),
    "fpe_violet_frustule": ("maurer_rose", 6),
    "fpe_magenta_plankton": ("curl_smoke", 3),
}


def _norm(a: np.ndarray) -> np.ndarray:
    out = np.asarray(a, np.float32)
    lo = float(out.min())
    span = float(np.ptp(out))
    return np.zeros_like(out) if span < 1e-7 else ((out - lo) / span).astype(np.float32)


def _circular_distance(a: float, b: float) -> float:
    d = abs((float(a) - float(b)) % 1.0)
    return min(d, 1.0 - d)


def _hues(recipe: Mapping) -> tuple[float, float, float]:
    raw = [float(x) % 1.0 for x in recipe.get("hues", ())]
    hero = raw[0] if raw else 0.86
    distinct = [h for h in raw[1:] if _circular_distance(h, hero) >= 0.14]
    opponent = distinct[0] if distinct else (hero + 0.43) % 1.0
    accent = next((h for h in raw[1:] if _circular_distance(h, hero) >= 0.08
                   and _circular_distance(h, opponent) >= 0.08),
                  (hero + 0.19) % 1.0)
    return hero, opponent, accent


def _palette15(recipe: Mapping) -> np.ndarray:
    hs = _hues(recipe)
    values = (0.16, 0.30, 0.46, 0.66, 0.90)
    out = np.empty((3, 5, 3), np.float32)
    for family, hue in enumerate(hs):
        for shade, value in enumerate(values):
            sat = min(0.96, 0.72 + family * 0.08 + shade * 0.025)
            out[family, shade] = colorsys.hsv_to_rgb(hue, sat, value)
    return out


def _source_for(fid: str) -> tuple[np.ndarray, Mapping]:
    mod = _bloom if fid.startswith("fbl_") else _petri
    recipe = mod.ALL[fid]
    engine_name, repeats = _EXOTIC_SOURCE_BY_ID[fid]
    # 160 is the audited inventory resolution.  Spatial repetition remaps the
    # coherent source field rather than stamping independent glyphs, retaining
    # its curves/adjacency/flow while shrinking primitives into the 2-8 work
    # pixel band.  There is no seed-per-tile noise and no secondary carrier.
    source_size = 160
    field = _exotic.field(engine_name, source_size, source_size, int(recipe["seed"]))
    yy, xx = np.mgrid[0:_DESIGN, 0:_DESIGN].astype(np.float32)
    scale = source_size * float(repeats) / float(_DESIGN)
    map_x = np.mod(xx * scale, source_size).astype(np.float32)
    map_y = np.mod(yy * scale, source_size).astype(np.float32)
    field = cv2.remap(field, map_x, map_y, cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_WRAP)
    return _norm(field), recipe


def _semantic_fields(source: np.ndarray, contour_count: int) -> dict[str, np.ndarray]:
    """Expose causal substructures of one unique source field.

    All marks are deterministic differential/topological consequences of the
    named generator.  There is deliberately no RNG or unrelated carrier.
    """
    smooth1 = cv2.GaussianBlur(source, (0, 0), 0.85)
    smooth2 = cv2.GaussianBlur(source, (0, 0), 2.15)
    gx = cv2.Sobel(smooth1, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(smooth1, cv2.CV_32F, 0, 1, ksize=3)
    edge = _norm(np.hypot(gx, gy))
    crest = _norm(np.maximum(smooth1 - smooth2, 0.0))
    trough = _norm(np.maximum(smooth2 - smooth1, 0.0))
    lap = cv2.Laplacian(smooth1, cv2.CV_32F, ksize=3)
    ridge = _norm(np.maximum(-lap, 0.0))
    valley = _norm(np.maximum(lap, 0.0))
    phase = np.mod(source * float(contour_count), 1.0)
    contour = np.clip(1.0 - np.abs(phase - 0.5) * 7.0, 0.0, 1.0).astype(np.float32)
    orient = (0.5 + 0.5 * np.cos(np.arctan2(gy, gx) * 4.0)) * np.sqrt(edge)
    orient = _norm(orient)
    harris = cv2.cornerHarris(np.clip(source * 255.0, 0, 255).astype(np.uint8), 3, 3, 0.045)
    node = _norm(np.maximum(harris, 0.0))
    gxx = cv2.Sobel(gx, cv2.CV_32F, 1, 0, ksize=3)
    gyy = cv2.Sobel(gy, cv2.CV_32F, 0, 1, ksize=3)
    gxy = cv2.Sobel(gx, cv2.CV_32F, 0, 1, ksize=3)
    saddle = _norm(np.abs(gxx * gyy - gxy * gxy))
    return {
        "source": source, "inverse": 1.0 - source, "edge": edge,
        "crest": crest, "trough": trough, "ridge": ridge,
        "valley": valley, "contour": contour, "orient": orient,
        "node": node, "saddle": saddle,
    }


_MODE_COMPONENTS = {
    "radial": ("source", "contour", "ridge", "node"),
    "woven": ("orient", "source", "edge", "crest"),
    "nodes": ("node", "source", "contour", "edge"),
    "flow": ("orient", "crest", "source", "edge"),
    "cells": ("source", "edge", "trough", "node"),
    "facets": ("source", "ridge", "valley", "edge"),
    "relief": ("source", "crest", "trough", "saddle"),
    "filament": ("edge", "ridge", "source", "node"),
    "labyrinth": ("ridge", "valley", "source", "contour"),
    "fronts": ("contour", "crest", "edge", "source"),
    "fracture": ("edge", "trough", "node", "source"),
    "bands": ("contour", "source", "ridge", "valley"),
    "saddles": ("saddle", "source", "edge", "contour"),
}


def _quantize_fixed(driver: np.ndarray, tiers: np.ndarray) -> np.ndarray:
    """Eight explicit shades with fixed thresholds, never equal occupancy."""
    idx = np.digitize(np.clip(driver, 0.0, 1.0), _FIXED_THRESHOLDS).astype(np.uint8)
    return tiers[idx]


_IDS = tuple(_bloom.ALL) + tuple(_petri.ALL)
_DRIVER_NAMES = ("source", "inverse", "edge", "crest", "trough",
                 "ridge", "valley", "contour", "orient", "node", "saddle")
_ALL_DRIVER_TRIPLETS = tuple(itertools.permutations(_DRIVER_NAMES, 3))
# Walk the 990 possible ordered ownership triples with a coprime stride.  The
# former first-40 slice accidentally kept ``source`` as the first driver for
# almost the whole shelf—different source topology, but needlessly similar
# channel ownership.  This deterministic spread is not a seed/rotation trick:
# the three selected fields are literal semantic derivatives of each source.
_DRIVER_TRIPLETS = tuple(
    _ALL_DRIVER_TRIPLETS[(53 + index * 137) % len(_ALL_DRIVER_TRIPLETS)]
    for index in range(len(_IDS))
)
assert (len(_IDS) == 40 and set(_IDS) == set(_SEMANTIC_MARKS)
        == set(_MODE_BY_ID) == set(_EXOTIC_SOURCE_BY_ID))
assert len({name for name, _repeat in _EXOTIC_SOURCE_BY_ID.values()}) == len(_IDS)
assert len(set(_DRIVER_TRIPLETS)) == len(_IDS)


@lru_cache(maxsize=6)
def _design_cached(fid: str) -> tuple[np.ndarray, np.ndarray]:
    source, recipe = _source_for(fid)
    index = _IDS.index(fid)
    fields = _semantic_fields(source, 3 + (index % 6))
    lead_name, opponent_name, accent_name, relief_name = _MODE_COMPONENTS[_MODE_BY_ID[fid]]
    lead = fields[lead_name]
    opponent = fields[opponent_name]
    accent = fields[accent_name]
    relief = fields[relief_name]

    # Paint: the original named field owns luma and silhouette.  The three
    # feature families select a finite 15-color bank; no stochastic texture
    # can create or alter the silhouette.
    family_scores = np.stack((
        0.70 * lead + 0.30 * fields["crest"],
        0.70 * opponent + 0.30 * fields["trough"],
        0.58 * accent + 0.24 * fields["node"] + 0.18 * fields["edge"],
    ), axis=2)
    family = np.argmax(family_scores, axis=2)
    shade_driver = _norm(0.58 * source + 0.18 * relief + 0.14 * fields["edge"]
                         + 0.10 * fields["contour"])
    shade = np.minimum(4, (shade_driver * 5.0).astype(np.int16))
    bank = _palette15(recipe)
    paint = bank[family, shade]
    # Keep the authored generator's relief dominant after color assignment.
    source_luma = 0.20 + 0.80 * source
    paint_luma = np.maximum(paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587
                            + paint[:, :, 2] * 0.114, 1e-4)
    paint = np.clip(paint * (source_luma / paint_luma)[..., None], 0.0, 1.0)
    # Purposeful feature-attached highlights: ridge lips, junctions, and the
    # selected relief family.  Their low amplitude cannot replace topology.
    feature_light = np.clip(0.16 * fields["ridge"] + 0.12 * fields["node"]
                            + 0.10 * relief, 0.0, 0.26)[..., None]
    paint = np.clip(paint * (1.0 - feature_light) + bank[2, 4] * feature_light,
                    0.0, 1.0).astype(np.float32)

    # Forty distinct driver triplets assign different M/R/Cc ownership.  The
    # named lead/opponent pair is additionally pushed in opposite directions
    # in M versus clearcoat: this is the Fractured A<->B handoff.
    dm_name, dr_name, dc_name = _DRIVER_TRIPLETS[index]
    affinity = _norm(lead) - _norm(opponent)
    dm = _norm(0.48 * fields[dm_name] + 0.22 * fields[lead_name]
               + 0.30 * np.clip(0.5 + 0.5 * affinity, 0.0, 1.0))
    dr = _norm(0.57 * fields[dr_name] + 0.27 * fields[relief_name]
               + 0.16 * fields["edge"])
    dc = _norm(0.48 * fields[dc_name] + 0.22 * fields[opponent_name]
               + 0.30 * np.clip(0.5 - 0.5 * affinity, 0.0, 1.0))
    # Fixed, source-independent contrast expansion widens deliberately quiet
    # derivatives enough to exercise the full material ladders.  It is not a
    # histogram/rank operation and never changes occupancy to satisfy a gate.
    dm = np.clip(0.5 + (dm - 0.5) * 1.80, 0.0, 1.0)
    dr = np.clip(0.5 + (dr - 0.5) * 1.80, 0.0, 1.0)
    dc = np.clip(0.5 + (dc - 0.5) * 1.80, 0.0, 1.0)
    spec = np.empty((_DESIGN, _DESIGN, 3), np.uint8)
    spec[:, :, 0] = _quantize_fixed(dm, _METAL_TIERS)
    spec[:, :, 1] = _quantize_fixed(dr, _ROUGH_TIERS)
    spec[:, :, 2] = _quantize_fixed(dc, _COAT_TIERS)
    return paint, spec


def make_entry(fid: str):
    if fid not in _SEMANTIC_MARKS:
        raise KeyError(fid)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        if src.shape[:2] != (fh, fw):
            src = cv2.resize(src, (fw, fh), interpolation=cv2.INTER_LINEAR)
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        authored, _ = _design_cached(fid)
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST)
        alpha = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - alpha) + authored * alpha, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        _, authored = _design_cached(fid)
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        calm = np.asarray([4.0, 120.0, 16.0], np.float32)
        active = np.clip(calm + (authored - calm) * max(0.0, float(sm)), 0.0, 255.0)
        mk = np.clip(m2, 0.0, 1.0)[..., None]
        rgb = active * mk + calm * (1.0 - mk)
        out = np.empty((fh, fw, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    paint_fn.__name__ = f"paint_{fid}_rejection_rebuild"
    spec_fn.__name__ = f"spec_{fid}_rejection_rebuild"
    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Override exactly the 40 rejected Bloom/Petri registry entries."""
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    loaded_engine = _sys.modules.get("shokker_engine_v2")
    if loaded_engine is not None and hasattr(loaded_engine, "FUSION_REGISTRY"):
        regs.append(loaded_engine.FUSION_REGISTRY)
    for fid in _IDS:
        entry = make_entry(fid)
        for reg in regs:
            reg[fid] = entry
    return "fractured-wilds Bloom/Petri rejection rebuild: 40 topology-owned overrides"


def clear_design_cache() -> None:
    _design_cached.cache_clear()


__all__ = ["install_into_engine", "make_entry", "clear_design_cache"]
