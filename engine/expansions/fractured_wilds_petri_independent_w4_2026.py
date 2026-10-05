# -*- coding: utf-8 -*-
"""Independent Petri I4: deterministic chaotic plankton mixing.

The module imports only raster/color validation primitives from I3; it does not
inherit I3's rejected seven-fold membrane carrier, paint, masks or spec.  I4
advects two plankton strains through a thirteen-kick area-preserving standard
map.  Source identity survives as Fractured A/B ownership while stretching,
folding, vorticity, near-collisions and transported chloroplast chemistry
produce literal secondary anatomy.  No RNG, noise texture, tile, row, hub,
stamp bank, shared palette router or shared spec substrate is used.

Candidate only; no registry/catalog/runtime wiring.  SPB-WILDS 2026-08-24.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import cv2
import numpy as np

from .fractured_wilds_petri_independent_w3_2026 import (
    Grammar, S, TAU, U, V, _blend, _dilate, _edge, _f, _n, _rgb,
    _soft_gt, _write,
)


def _standard_map_history():
    x = U.copy()
    y = V.copy()
    golden = .61803398875
    # Reverse thirteen area-preserving kicks.  The changing incommensurate
    # phases prevent a periodic grid while retaining exact deterministic flow.
    for step in reversed(range(13)):
        phase_a = np.mod((step + 1) * golden, 1.0)
        phase_b = np.mod((step + 1) * .41421356237, 1.0)
        kx = .112 + .026 * np.sin((step + 1) * 1.173)
        ky = .127 + .023 * np.cos((step + 1) * .937)
        y = np.mod(y - ky * np.sin(TAU * (x + phase_b)), 1.0)
        x = np.mod(x - kx * np.sin(TAU * (y + phase_a)), 1.0)
    return x.astype(np.float32), y.astype(np.float32)


def _tiered_color(field, colors):
    thresholds = np.linspace(.09, .91, len(colors) - 1, dtype=np.float32)
    index = np.digitize(_f(field), thresholds)
    return np.asarray(colors, np.float32)[index]


def i4_amber_plankton(history_fn=_standard_map_history, source_phase_fn=None,
                      detail_profile="base", spec_profile="mask_write") -> Grammar:
    source_x, source_y = history_fn()
    # Two continuous strains at inoculation.  After thirteen kicks the source
    # boundary is folded through the whole frame but never becomes a noise map.
    if source_phase_fn is None:
        source_phase = (np.sin(TAU * (source_x + .21 * np.sin(TAU * source_y)))
                        + .37 * np.cos(TAU * (2.0 * source_y - .43 * source_x)))
    else:
        source_phase = np.asarray(source_phase_fn(source_x, source_y), np.float32)
    micro_profile = detail_profile == "micro"
    # The micro culture reserves a real neutral interface corridor.  Besides
    # making reactions legible, this caps every measured primary-strain width:
    # both binary carriers remain <=28.8 native pixels in the final I7 field.
    strain_gate = .45 if micro_profile else .05
    strain_a = _soft_gt(source_phase, strain_gate, .18)
    strain_b = _soft_gt(-source_phase, strain_gate, .18)
    mixing_front = _f((.16 - np.abs(source_phase)) / .11 + .5)
    if micro_profile:
        # I7: two narrow material flanks around the culture interface.  The
        # generic morphology edge engulfed 84% of a high-frequency culture and
        # visually bleached the field; this analytic band stays causal and fine.
        front_lips = np.exp(
            -np.square((np.abs(source_phase) - .115) / .030)
        ).astype(np.float32)
    else:
        front_lips = _edge(_soft_gt(source_phase, 0.0, .045), 1)

    gy, gx = np.gradient(source_phase)
    magnitude = np.hypot(gx, gy) + 1e-6
    nx, ny = gx / magnitude, gy / magnitude
    curvature = np.gradient(nx, axis=1) + np.gradient(ny, axis=0)
    stretch = _n(np.log1p(magnitude))
    bend = _n(np.abs(curvature))
    fine_profile = detail_profile in ("fine", "micro")
    stretched_filaments = _f(
        mixing_front * _soft_gt(stretch,
                                .30 if fine_profile else .56,
                                .12 if fine_profile else .18))
    folded_wave_tips = _f(mixing_front * _soft_gt(bend, .61, .18))

    # Periodic displacement is measured on the circle, avoiding wrap seams.
    dx = np.angle(np.exp(1j * TAU * (source_x - U))).astype(np.float32) / TAU
    dy = np.angle(np.exp(1j * TAU * (source_y - V))).astype(np.float32) / TAU
    vorticity = np.gradient(dy, axis=1) - np.gradient(dx, axis=0)
    shear_eddies = _f(_soft_gt(_n(np.abs(vorticity)),
                               .015 if fine_profile else .61,
                               .008 if fine_profile else .18)
                      * (.34 + .66 * mixing_front))

    local_front_density = cv2.boxFilter(mixing_front, cv2.CV_32F,
                                        (9, 9), normalize=True)
    collision_knots = _f(
        mixing_front
        * _soft_gt(local_front_density,
                   .18 if fine_profile else .29,
                   .07 if fine_profile else .09)
        * _soft_gt(stretch,
                   .22 if fine_profile else .45,
                   .11 if fine_profile else .20))

    # Chloroplasts and feeding grooves are advected source chemistry, so every
    # colored event moves causally with its parent strain.
    chlorophyll_phase = np.cos(TAU * (5.0 * source_x + 3.0 * source_y
                                      + .19 * np.sin(TAU * source_y)))
    chloroplast_bands = _f(strain_a * _soft_gt(chlorophyll_phase, .57, .20))
    feeding_phase = np.sin(TAU * (2.0 * source_x - 7.0 * source_y))
    feeding_grooves = _f(strain_b * _soft_gt(feeding_phase, .68, .17)
                         * (.28 + .72 * stretch))
    rupture_phase = np.cos(TAU * (11.0 * source_x + source_y))
    ruptured_fronts = _f(front_lips * _soft_gt(rupture_phase, .80, .12)
                         * _soft_gt(stretch, .47, .22))

    # Low-stretch material trapped between folds becomes daughter bloom tissue.
    daughter_blooms = _f((strain_a * strain_b + .45 * mixing_front)
                         * _soft_gt(1.0 - stretch, .60, .19)
                         * _soft_gt(np.sin(TAU * (source_x + 4.0 * source_y)),
                                    .58, .20))

    masks = {
        "amber_parent_strain": strain_a,
        "violet_daughter_strain": strain_b,
        "mixing_front": mixing_front,
        "paired_front_lips": front_lips,
        "stretched_filaments": stretched_filaments,
        "shear_eddies": shear_eddies,
        "collision_knots": collision_knots,
        "transported_chloroplast_bands": chloroplast_bands,
        "feeding_grooves": feeding_grooves,
        "ruptured_fronts": ruptured_fronts,
        "daughter_bloom_tissue": daughter_blooms,
    }
    banks = {
        "amber_parent_strain": "A",
        "violet_daughter_strain": "B",
        "mixing_front": "N",
        "paired_front_lips": "A",
        "stretched_filaments": "A",
        "shear_eddies": "B",
        "collision_knots": "A",
        "transported_chloroplast_bands": "A",
        "feeding_grooves": "B",
        "ruptured_fronts": "A",
        "daughter_bloom_tissue": "B",
    }

    # Twelve authored shades expose internal strain history; the H/S/B slider
    # cannot turn another topology into this material.
    amber_bank = [_rgb(code) for code in (
        "#29120a", "#4a1d08", "#6c2b08", "#8f3d08", "#b55309", "#d76c0b",
        "#ee8b13", "#f9aa27", "#ffc849", "#ffdf72", "#fff0a4", "#fff7d0")]
    violet_bank = [_rgb(code) for code in (
        "#10091f", "#201038", "#321653", "#471d70", "#5e278c", "#7935a8",
        "#9848c0", "#ba62d5", "#d57de5", "#e99cf0", "#f5bdf7", "#ffe0ff")]
    tone_a = _n(.57 * stretch + .28 * _n(source_x) + .15 * _n(np.abs(vorticity)))
    tone_b = _n(.55 * bend + .27 * _n(source_y) + .18 * (1.0 - stretch))
    color_a = _tiered_color(tone_a, amber_bank)
    color_b = _tiered_color(tone_b, violet_bank)
    paint = np.broadcast_to(_rgb("#080710"), (S, S, 3)).copy()
    paint = paint * (1.0 - .94 * strain_a[..., None]) + color_a * (.94 * strain_a[..., None])
    paint = paint * (1.0 - .94 * strain_b[..., None]) + color_b * (.94 * strain_b[..., None])
    paint = _blend(paint, _rgb("#16121e"),
                   (.20 if micro_profile else .54) * mixing_front)
    paint = _blend(paint, _rgb("#ffe7ad"),
                   (.46 if micro_profile else .84) * front_lips)
    paint = _blend(paint, _rgb("#ffb92e"),
                   (.58 if micro_profile else .91) * stretched_filaments)
    paint = _blend(paint, _rgb("#26d8e8"),
                   (.30 if micro_profile else .91) * shear_eddies)
    paint = _blend(paint, _rgb("#fff5d2"), .95 * collision_knots)
    paint = _blend(paint, _rgb("#8cff48"), .95 * chloroplast_bands)
    paint = _blend(paint, _rgb("#36c7ff"), .93 * feeding_grooves)
    paint = _blend(paint, _rgb("#ff5538"), .98 * ruptured_fronts)
    paint = _blend(paint, _rgb("#ff5dc8"), .92 * daughter_blooms)

    hue_null = np.full((S, S), .04, np.float32)
    for name, level in (
        ("amber_parent_strain", .35), ("violet_daughter_strain", .57),
        ("mixing_front", .12), ("paired_front_lips", .88),
        ("stretched_filaments", .76),
        ("shear_eddies", .63), ("collision_knots", .98),
        ("transported_chloroplast_bands", .82), ("feeding_grooves", .73),
        ("ruptured_fronts", .93), ("daughter_bloom_tissue", .61),
    ):
        hue_null = hue_null * (1.0 - masks[name]) + level * masks[name]
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    if spec_profile == "orthogonal_history":
        # I7: each literal material channel follows a different physical
        # observable.  This deliberately avoids the rejected pattern of three
        # recolored writes over one shared mask stack.
        platelet_phase = _f(
            .5 + .5 * np.sin(TAU * (
                17.0 * source_x + 11.0 * source_y
                + .17 * np.sin(TAU * (5.0 * source_y - source_x))
            ))
        )
        metal_field = _f(
            .08 + .62 * strain_a * (.16 + .84 * platelet_phase)
            + .22 * front_lips + .20 * chloroplast_bands
            + .17 * collision_knots - .13 * feeding_grooves
        )

        # Roughness is deformation history: compression remains matte while
        # high stretch and vorticity polish the daughter strain.  Its topology
        # is a continuous shear field, not the metallic platelet tracks.
        compression = _n(np.maximum(-curvature, 0.0))
        shear_polish = _f(.56 * stretch + .44 * _n(np.abs(vorticity)))
        rough_field = _f(
            .14 + .42 * compression + .34 * (1.0 - shear_polish)
            + .24 * feeding_grooves + .12 * daughter_blooms
            - .21 * stretched_filaments - .18 * collision_knots
        )

        # Clearcoat is deposited only by interface polymerisation events:
        # curved lips, collisions, ruptures and daughter tissue.  This produces
        # an intermittent reaction network distinct from both fields above.
        interface_reaction = _f(
            .44 * mixing_front * (.18 + .82 * bend)
            + .42 * front_lips * (.20 + .80 * stretch)
            + .40 * collision_knots + .31 * ruptured_fronts
            + .28 * daughter_blooms
        )
        metal = np.clip(10.0 + 242.0 * metal_field, 0, 255).astype(np.float32)
        rough = np.clip(18.0 + 224.0 * rough_field, 0, 255).astype(np.float32)
        coat = np.clip(
            7.0 + 247.0 * np.sqrt(interface_reaction), 0, 255
        ).astype(np.float32)
    else:
        metal = _write(8, masks, (
            ("amber_parent_strain", 186), ("violet_daughter_strain", 29),
            ("mixing_front", 83), ("paired_front_lips", 222),
            ("stretched_filaments", 248),
            ("shear_eddies", 72), ("collision_knots", 252),
            ("transported_chloroplast_bands", 203), ("feeding_grooves", 94),
            ("ruptured_fronts", 233), ("daughter_bloom_tissue", 51),
        ))
        rough = _write(238, masks, (
            ("amber_parent_strain", 68), ("violet_daughter_strain", 191),
            ("mixing_front", 149), ("paired_front_lips", 96),
            ("stretched_filaments", 38),
            ("shear_eddies", 167), ("collision_knots", 24),
            ("transported_chloroplast_bands", 83), ("feeding_grooves", 207),
            ("ruptured_fronts", 214), ("daughter_bloom_tissue", 178),
        ))
        coat = _write(6, masks, (
            ("amber_parent_strain", 33), ("violet_daughter_strain", 211),
            ("mixing_front", 107), ("paired_front_lips", 174),
            ("stretched_filaments", 79),
            ("shear_eddies", 246), ("collision_knots", 254),
            ("transported_chloroplast_bands", 154), ("feeding_grooves", 239),
            ("ruptured_fronts", 123), ("daughter_bloom_tissue", 225),
        ))

    marks = tuple((name, _f(mask), banks[name]) for name, mask in masks.items())
    flat = [name for name, mask, _owner in marks if float(mask.std()) < .0015]
    if flat:
        raise ValueError(f"I4 Amber Plankton has flat causal families: {flat}")
    return Grammar(marks, _f(paint), _f(hue_null),
                   tuple(np.asarray(ch, np.float32) for ch in (metal, rough, coat)))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fpe_amber_plankton": i4_amber_plankton,
}
HUES = {"fpe_amber_plankton": (.09, .51)}
PETRI_IDS = tuple(BUILDERS)


@lru_cache(maxsize=20)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    return grammar.paint, np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)


def clear_cache():
    _authored.cache_clear()


def debug_grammar(fid: str):
    return BUILDERS[fid]()


def debug_hue_null(fid: str):
    return debug_grammar(fid).hue_null


def owner_unions(grammar: Grammar):
    out = {key: np.zeros((S, S), np.float32) for key in ("A", "B", "N")}
    for _name, mask, owner in grammar.marks:
        out[owner] = np.maximum(out[owner], mask)
    return out


def debug_angle_pair(fid: str):
    paint, spec = _authored(fid)
    owners = owner_unions(debug_grammar(fid))
    metal, rough, coat = (spec[:, :, i].astype(np.float32) / 255.0 for i in range(3))
    aperture = np.clip(1.0 - .52 * rough, .22, 1.0)
    la = np.clip(.09 + 1.12 * metal * aperture + .35 * owners["A"] - .10 * owners["B"], .08, 1.28)
    lb = np.clip(.09 + 1.12 * coat * aperture + .35 * owners["B"] - .10 * owners["A"], .08, 1.28)
    a = np.clip(paint * la[..., None] + np.asarray((.25, .06, .008), np.float32)
                * (metal * aperture * (.44 + .56 * owners["A"]))[..., None], 0, 1)
    b = np.clip(paint * lb[..., None] + np.asarray((.008, .10, .26), np.float32)
                * (coat * aperture * (.44 + .56 * owners["B"]))[..., None], 0, 1)
    return a.astype(np.float32), b.astype(np.float32), np.abs(a - b).astype(np.float32)


__all__ = ["BUILDERS", "Grammar", "HUES", "PETRI_IDS", "_authored",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "owner_unions"]
