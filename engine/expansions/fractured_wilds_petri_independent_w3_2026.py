# -*- coding: utf-8 -*-
"""Independent Petri I3: chaotic-advection membrane, one-ID evidence wave.

I1 line-cloud polymer and I2 gyroid paver are frozen rejections.  I3 uses a
different physical silhouette: two initially continuous membrane fluids are
stretched and folded by a deterministic alternating-sine flow.  The process
creates one globally connected lamellar history rather than stamps, tiles,
rows, hubs, specimens or random texture.  The Lagrangian source coordinates
remain available, so interfaces, stretch ridges, fold cusps, fusion necks,
transported protein rafts, rupture scars and enclosed vesicles are causal.

Candidate only; no registry/catalog/runtime wiring.  SPB-WILDS 2026-08-24.
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


def _transport_coordinates():
    """Back-advect every output pixel through an analytic incompressible map."""
    x = U.copy()
    y = V.copy()
    # Reverse the seven-step alternating sine flow.  Coefficients are fixed and
    # incommensurate; variation is process history, never an RNG/seed texture.
    steps = (
        ("y", .153, .071), ("x", -.187, .263), ("y", .219, .417),
        ("x", .171, .613), ("y", -.143, .829), ("x", .207, 1.073),
        ("y", .181, 1.337),
    )
    for axis, amplitude, phase in reversed(steps):
        if axis == "x":
            x = np.mod(x - amplitude * np.sin(TAU * (y + phase)), 1.0)
        else:
            y = np.mod(y - amplitude * np.sin(TAU * (x + phase)), 1.0)
    return x.astype(np.float32), y.astype(np.float32)


def _enclosed_vesicle_edges(binary):
    count, labels, stats, _centres = cv2.connectedComponentsWithStats(
        np.uint8(binary), 8, cv2.CV_32S)
    selected = np.zeros((S, S), np.float32)
    for label in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[label])
        touches = x <= 0 or y <= 0 or x + w >= S or y + h >= S
        if not touches and 18 <= area <= 520 and 4 <= w <= 28 and 4 <= h <= 28:
            selected[labels == label] = 1.0
    return _edge(selected, 1)


def i3_cyan_membrane() -> Grammar:
    source_x, source_y = _transport_coordinates()
    # One broad material interface at inoculation time, then seven folds.  The
    # secondary harmonic breaks mirror symmetry but does not supply texture.
    material = (np.sin(TAU * (source_x + .18 * np.sin(TAU * source_y)))
                + .29 * np.sin(TAU * (2.0 * source_y - .37 * source_x)))
    material = material.astype(np.float32)
    cyan_sheet = _soft_gt(material, .07, .16)
    magenta_sheet = _soft_gt(-material, .07, .16)
    bilayer_interface = _f((.15 - np.abs(material)) / .10 + .5)
    interface_lips = _edge(_soft_gt(material, 0.0, .045), 1)

    gy, gx = np.gradient(material)
    magnitude = np.hypot(gx, gy) + 1e-6
    nx, ny = gx / magnitude, gy / magnitude
    curvature = np.gradient(nx, axis=1) + np.gradient(ny, axis=0)
    stretch = _n(np.log1p(magnitude))
    cusp_score = _n(np.abs(curvature))
    stretch_ridges = _f(bilayer_interface * _soft_gt(stretch, .58, .18))
    fold_cusps = _f(bilayer_interface * _soft_gt(cusp_score, .63, .17))

    local_interface_density = cv2.boxFilter(
        bilayer_interface, cv2.CV_32F, (11, 11), normalize=True)
    fusion_necks = _f(bilayer_interface
                      * _soft_gt(local_interface_density, .28, .10)
                      * _soft_gt(stretch, .42, .22))

    # Protein concentration is a transported source-space chemistry field.
    protein_phase = np.sin(TAU * (3.0 * source_x + 5.0 * source_y
                                  + .21 * np.sin(TAU * source_x)))
    protein_rafts = _f(bilayer_interface * _soft_gt(protein_phase, .63, .18))
    rupture_phase = np.cos(TAU * (7.0 * source_x - 2.0 * source_y))
    rupture_scars = _f(interface_lips * _soft_gt(rupture_phase, .78, .12)
                       * _soft_gt(stretch, .50, .20))

    # Closed material pockets on a periodic flow often remain connected through
    # a one-pixel neck.  Detect distance maxima inside each advected phase, then
    # expose only chemistry-selected pocket throats (not a free dot texture).
    pocket_cores = np.zeros((S, S), np.float32)
    pocket_selector = _soft_gt(
        np.cos(TAU * (1.73 * source_x + 2.31 * source_y)), .74, .15)
    for phase_binary in (cyan_sheet > .72, magenta_sheet > .72):
        distance = cv2.distanceTransform(np.uint8(phase_binary), cv2.DIST_L2, 5)
        peaks = (distance >= cv2.dilate(distance, np.ones((7, 7), np.uint8))).astype(np.float32)
        pocket_cores = np.maximum(
            pocket_cores,
            peaks * _soft_gt(distance, 2.2, .8) * pocket_selector,
        )
    vesicle_rims = _edge(_dilate(pocket_cores, 2), 1)

    # Curvature polarity separates genuine saddle-side and cup-side anatomy.
    negative_bend = _n(np.maximum(-curvature, 0.0))
    saddle_side = _f(fold_cusps * _soft_gt(negative_bend, .34, .20))

    masks = {
        "cyan_advected_lipid": cyan_sheet,
        "magenta_conjugate_medium": magenta_sheet,
        "bilayer_interface": bilayer_interface,
        "paired_interface_lips": interface_lips,
        "high_stretch_lamellae": stretch_ridges,
        "saddle_fold_cusps": saddle_side,
        "fusion_necks": fusion_necks,
        "transported_protein_rafts": protein_rafts,
        "rupture_scars": rupture_scars,
        "enclosed_vesicle_rims": vesicle_rims,
    }
    banks = {
        "cyan_advected_lipid": "A",
        "magenta_conjugate_medium": "B",
        "bilayer_interface": "N",
        "paired_interface_lips": "A",
        "high_stretch_lamellae": "A",
        "saddle_fold_cusps": "A",
        "fusion_necks": "B",
        "transported_protein_rafts": "B",
        "rupture_scars": "A",
        "enclosed_vesicle_rims": "B",
    }

    paint = np.broadcast_to(_rgb("#071923"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#087d96"), .91 * cyan_sheet)
    paint = _blend(paint, _rgb("#811761"), .91 * magenta_sheet)
    paint = _blend(paint, _rgb("#152532"), .64 * bilayer_interface)
    paint = _blend(paint, _rgb("#81efff"), .87 * interface_lips)
    paint = _blend(paint, _rgb("#11cddd"), .92 * stretch_ridges)
    paint = _blend(paint, _rgb("#d5f5ff"), .94 * saddle_side)
    paint = _blend(paint, _rgb("#79ff8f"), .95 * fusion_necks)
    paint = _blend(paint, _rgb("#ffd32c"), .96 * protein_rafts)
    paint = _blend(paint, _rgb("#ff6b36"), .98 * rupture_scars)
    paint = _blend(paint, _rgb("#f2fbff"), .98 * vesicle_rims)

    hue_null = np.full((S, S), .05, np.float32)
    for name, level in (
        ("cyan_advected_lipid", .36), ("magenta_conjugate_medium", .58),
        ("bilayer_interface", .13), ("paired_interface_lips", .83),
        ("high_stretch_lamellae", .72), ("saddle_fold_cusps", .93),
        ("fusion_necks", .79),
        ("transported_protein_rafts", .97), ("rupture_scars", .88),
        ("enclosed_vesicle_rims", .99),
    ):
        hue_null = hue_null * (1.0 - masks[name]) + level * masks[name]
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    metal = _write(9, masks, (
        ("cyan_advected_lipid", 184), ("magenta_conjugate_medium", 31),
        ("bilayer_interface", 78), ("paired_interface_lips", 218),
        ("high_stretch_lamellae", 244), ("saddle_fold_cusps", 252),
        ("fusion_necks", 162),
        ("transported_protein_rafts", 230), ("rupture_scars", 202),
        ("enclosed_vesicle_rims", 248),
    ))
    rough = _write(232, masks, (
        ("cyan_advected_lipid", 69), ("magenta_conjugate_medium", 194),
        ("bilayer_interface", 151), ("paired_interface_lips", 104),
        ("high_stretch_lamellae", 47), ("saddle_fold_cusps", 29),
        ("fusion_necks", 88),
        ("transported_protein_rafts", 42), ("rupture_scars", 213),
        ("enclosed_vesicle_rims", 22),
    ))
    coat = _write(7, masks, (
        ("cyan_advected_lipid", 38), ("magenta_conjugate_medium", 211),
        ("bilayer_interface", 113), ("paired_interface_lips", 172),
        ("high_stretch_lamellae", 82), ("saddle_fold_cusps", 66),
        ("fusion_necks", 249),
        ("transported_protein_rafts", 242), ("rupture_scars", 128),
        ("enclosed_vesicle_rims", 254),
    ))

    marks = tuple((name, _f(mask), banks[name]) for name, mask in masks.items())
    flat = [name for name, mask, _owner in marks if float(mask.std()) < .0015]
    if flat:
        raise ValueError(f"I3 Cyan Membrane has flat causal families: {flat}")
    return Grammar(marks, _f(paint), _f(hue_null),
                   tuple(np.asarray(ch, np.float32) for ch in (metal, rough, coat)))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fpe_cyan_membrane": i3_cyan_membrane,
}
HUES = {"fpe_cyan_membrane": (.50, .91)}
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
    a = np.clip(paint * la[..., None] + np.asarray((.24, .06, .01), np.float32)
                * (metal * aperture * (.44 + .56 * owners["A"]))[..., None], 0, 1)
    b = np.clip(paint * lb[..., None] + np.asarray((.01, .10, .25), np.float32)
                * (coat * aperture * (.44 + .56 * owners["B"]))[..., None], 0, 1)
    return a.astype(np.float32), b.astype(np.float32), np.abs(a - b).astype(np.float32)


__all__ = ["BUILDERS", "Grammar", "HUES", "PETRI_IDS", "_authored",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "owner_unions"]
