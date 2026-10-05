# -*- coding: utf-8 -*-
"""Independent Petri I2: one true triply-periodic membrane candidate.

I1 Violet Chains was frozen as REBUILD after its contact reduced to a line
cloud.  I2 changes both finish and physical process.  ``fpe_violet_membrane``
is authored from a warped three-dimensional gyroid slice at native-fine cell
scale.  It is the sole Petri candidate allowed to use an interpenetrating
organic labyrinth.  The visible anatomy is the signed pair of conjugate lipid
channels plus the minimal-surface midplane, negative-curvature saddles, necks,
fusion seams, cleavage scars, transmembrane protein rafts and vesicle throats.

No RNG, texture noise, tile, stamp bank, shared palette router or shared spec
substrate is used.  Candidate only; no registry/catalog/runtime wiring.
SPB-WILDS 2026-08-24, owner doctrine 8--32 px native and literal A/B flip.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np


S = 512
Y, X = np.mgrid[0:S, 0:S].astype(np.float32)
U = (X + .5) / S
V = (Y + .5) / S
TAU = np.float32(2.0 * np.pi)


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    hue_null: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]


def _f(value):
    return np.clip(np.asarray(value, np.float32), 0.0, 1.0)


def _n(value):
    value = np.nan_to_num(np.asarray(value, np.float32))
    lo, hi = float(value.min()), float(value.max())
    if hi - lo < 1.0e-7:
        return np.zeros(value.shape, np.float32)
    return ((value - lo) / (hi - lo)).astype(np.float32)


def _soft_gt(value, threshold, feather=.035):
    return _f((np.asarray(value, np.float32) - float(threshold)) / float(feather) + .5)


def _band(value, centre, width, feather=.025):
    return _f((float(width) - np.abs(np.asarray(value, np.float32) - float(centre)))
              / float(feather) + .5)


def _dilate(value, radius=1):
    k = np.ones((2 * int(radius) + 1,) * 2, np.uint8)
    return _f(cv2.dilate(_f(value), k))


def _erode(value, radius=1):
    k = np.ones((2 * int(radius) + 1,) * 2, np.uint8)
    return _f(cv2.erode(_f(value), k))


def _edge(value, radius=1):
    return _f(_dilate(value, radius) - _erode(value, radius))


def _rgb(code):
    code = code.removeprefix("#")
    return np.asarray(tuple(int(code[i:i + 2], 16) for i in (0, 2, 4)),
                      np.float32) / 255.0


def _blend(canvas, color, alpha):
    alpha = _f(alpha)[..., None]
    return canvas * (1.0 - alpha) + np.asarray(color, np.float32) * alpha


def _write(base, masks, recipe):
    out = np.full((S, S), float(base), np.float32)
    for name, target in recipe:
        alpha = _f(masks[name])
        out = out * (1.0 - alpha) + float(target) * alpha
    return np.clip(out, 0.0, 255.0).astype(np.float32)


def _phase_zero(phase, width=.16):
    return _f((float(width) - np.abs(np.sin(np.asarray(phase, np.float32))))
              / max(.02, float(width) * .38) + .5)


def i2_violet_membrane() -> Grammar:
    # A deterministic nonuniform 3-D cut.  Incommensurate phase warps destroy
    # visible cell repetition without introducing a random/noise field.
    px = TAU * (39.0 * U
                + .72 * np.sin(TAU * (1.27 * V + .31 * U))
                + .31 * np.sin(TAU * (2.11 * V - .47 * U)))
    py = TAU * (43.0 * V
                + .63 * np.sin(TAU * (.93 * U - .29 * V))
                + .27 * np.cos(TAU * (1.71 * U + .41 * V)))
    pz = TAU * (.34 * U - .29 * V
                + .71 * np.sin(TAU * (1.13 * U + .67 * V))
                + .39 * np.cos(TAU * (.57 * U - 1.49 * V)))

    gyroid = (np.sin(px) * np.cos(py)
              + np.sin(py) * np.cos(pz)
              + np.sin(pz) * np.cos(px)).astype(np.float32)
    # The signed channels occupy almost all paint; the surface is a fine seam,
    # not a set of large isolated blobs on a dark ground.
    channel_a = _soft_gt(gyroid, .10, .18)
    channel_b = _soft_gt(-gyroid, .10, .18)
    midplane = _f((.20 - np.abs(gyroid)) / .13 + .5)
    bilayer_lips = _edge(_soft_gt(gyroid, 0.0, .05), 1)

    gy, gx = np.gradient(gyroid)
    gyy, gyx = np.gradient(gy)
    gxy, gxx = np.gradient(gx)
    gradient = _n(np.hypot(gx, gy))
    hessian_det = gxx * gyy - .25 * (gxy + gyx) ** 2
    negative_curvature = _n(np.maximum(-hessian_det, 0.0))
    positive_curvature = _n(np.maximum(hessian_det, 0.0))
    saddle_patches = _f(midplane * _soft_gt(negative_curvature, .55, .20))
    conjugate_necks = _f(midplane * _soft_gt(gradient, .62, .16))

    # Chemistry lives on the gyroid anatomy.  These quasiperiodic selectors do
    # not make a second carrier; they segment the one membrane into causal
    # events whose positions move when the physical surface moves.
    raft_phase = .173 * px + .241 * py - .119 * pz
    protein_rafts = _f(midplane * _soft_gt(np.cos(raft_phase), .72, .18))
    cleavage_phase = .091 * px - .137 * py + .317 * pz
    cleavage_scars = _f(bilayer_lips * _phase_zero(cleavage_phase, .13))
    fusion_phase = .223 * px + .077 * py + .281 * pz
    fusion_necks = _f(conjugate_necks * _soft_gt(np.sin(fusion_phase), .38, .24))

    # Vesicle throats are local maxima of channel distance, explicitly tied to
    # the positive-curvature chambers and thinned to 8--24 native pixels.
    binary_b = np.uint8(channel_b > .62)
    distance = cv2.distanceTransform(binary_b, cv2.DIST_L2, 5).astype(np.float32)
    maxima = (distance >= cv2.dilate(distance, np.ones((5, 5), np.uint8))).astype(np.float32)
    chamber_select = _soft_gt(np.sin(.137 * px + .193 * py - .071 * pz), .70, .18)
    vesicle_cores = _f(maxima * _soft_gt(distance, 2.0, .8)
                       * positive_curvature * chamber_select)
    vesicle_cores = _dilate(vesicle_cores, 2)
    vesicle_throats = _edge(vesicle_cores, 1)

    masks = {
        "violet_lipid_channel": channel_a,
        "cyan_conjugate_channel": channel_b,
        "minimal_surface_midplane": midplane,
        "bilayer_lips": bilayer_lips,
        "negative_curvature_saddles": saddle_patches,
        "high_gradient_necks": conjugate_necks,
        "transmembrane_protein_rafts": protein_rafts,
        "cleavage_scars": cleavage_scars,
        "fusion_necks": fusion_necks,
        "vesicle_throats": vesicle_throats,
    }
    banks = {
        "violet_lipid_channel": "A",
        "cyan_conjugate_channel": "B",
        "minimal_surface_midplane": "N",
        "bilayer_lips": "A",
        "negative_curvature_saddles": "A",
        "high_gradient_necks": "B",
        "transmembrane_protein_rafts": "B",
        "cleavage_scars": "A",
        "fusion_necks": "B",
        "vesicle_throats": "B",
    }

    # Literal material paint; there is no reusable palette compositor.
    paint = np.broadcast_to(_rgb("#160b2d"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#7a24b8"), .93 * channel_a)
    paint = _blend(paint, _rgb("#08a7bf"), .91 * channel_b)
    paint = _blend(paint, _rgb("#22103e"), .40 * midplane)
    paint = _blend(paint, _rgb("#ebc8ff"), .80 * bilayer_lips)
    paint = _blend(paint, _rgb("#ff4bc8"), .92 * saddle_patches)
    paint = _blend(paint, _rgb("#21f1df"), .93 * conjugate_necks)
    paint = _blend(paint, _rgb("#ffc928"), .96 * protein_rafts)
    paint = _blend(paint, _rgb("#ff7741"), .96 * cleavage_scars)
    paint = _blend(paint, _rgb("#78ff9a"), .95 * fusion_necks)
    paint = _blend(paint, _rgb("#f3f7ff"), .98 * vesicle_throats)

    hue_null = np.full((S, S), .06, np.float32)
    for name, level in (
        ("violet_lipid_channel", .31), ("cyan_conjugate_channel", .58),
        ("minimal_surface_midplane", .15), ("bilayer_lips", .87),
        ("negative_curvature_saddles", .71), ("high_gradient_necks", .79),
        ("transmembrane_protein_rafts", .95), ("cleavage_scars", .63),
        ("fusion_necks", .84), ("vesicle_throats", .99),
    ):
        hue_null = hue_null * (1.0 - masks[name]) + level * masks[name]
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    metal = _write(14, masks, (
        ("violet_lipid_channel", 171), ("cyan_conjugate_channel", 38),
        ("minimal_surface_midplane", 82), ("bilayer_lips", 218),
        ("negative_curvature_saddles", 246), ("high_gradient_necks", 124),
        ("transmembrane_protein_rafts", 232), ("cleavage_scars", 196),
        ("fusion_necks", 109), ("vesicle_throats", 252),
    ))
    rough = _write(226, masks, (
        ("violet_lipid_channel", 72), ("cyan_conjugate_channel", 186),
        ("minimal_surface_midplane", 145), ("bilayer_lips", 91),
        ("negative_curvature_saddles", 49), ("high_gradient_necks", 130),
        ("transmembrane_protein_rafts", 42), ("cleavage_scars", 206),
        ("fusion_necks", 101), ("vesicle_throats", 28),
    ))
    coat = _write(9, masks, (
        ("violet_lipid_channel", 31), ("cyan_conjugate_channel", 207),
        ("minimal_surface_midplane", 104), ("bilayer_lips", 168),
        ("negative_curvature_saddles", 74), ("high_gradient_necks", 226),
        ("transmembrane_protein_rafts", 245), ("cleavage_scars", 116),
        ("fusion_necks", 251), ("vesicle_throats", 254),
    ))

    marks = tuple((name, _f(mask), banks[name]) for name, mask in masks.items())
    if any(float(mask.std()) < .0015 for _name, mask, _owner in marks):
        raise ValueError("I2 Violet Membrane has a visually flat causal family")
    return Grammar(marks, _f(paint), _f(hue_null),
                   tuple(np.asarray(ch, np.float32) for ch in (metal, rough, coat)))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fpe_violet_membrane": i2_violet_membrane,
}
HUES = {"fpe_violet_membrane": (.78, .37)}
PETRI_IDS = tuple(BUILDERS)


@lru_cache(maxsize=20)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    spec = np.stack(grammar.explicit_spec, axis=2)
    return grammar.paint, np.clip(spec, 0, 255).astype(np.uint8)


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
    la = np.clip(.09 + 1.12 * metal * aperture + .35 * owners["A"]
                 - .10 * owners["B"], .08, 1.28)
    lb = np.clip(.09 + 1.12 * coat * aperture + .35 * owners["B"]
                 - .10 * owners["A"], .08, 1.28)
    a = np.clip(paint * la[..., None]
                + np.asarray((.24, .06, .01), np.float32)
                * (metal * aperture * (.44 + .56 * owners["A"]))[..., None], 0, 1)
    b = np.clip(paint * lb[..., None]
                + np.asarray((.01, .10, .25), np.float32)
                * (coat * aperture * (.44 + .56 * owners["B"]))[..., None], 0, 1)
    return a.astype(np.float32), b.astype(np.float32), np.abs(a - b).astype(np.float32)


__all__ = ["BUILDERS", "Grammar", "HUES", "PETRI_IDS", "_authored",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "owner_unions"]
