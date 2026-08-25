# -*- coding: utf-8 -*-
"""Independent Petri I7: micro-lamellar Amber Plankton repair.

I6 established a unique, deterministic chaotic-advection family but its broad
inoculation bands enlarged to 40--160 px after the engine's 512 -> 2048 scale.
I7 keeps the same one-finish physical history and replaces only the initial
plankton culture with incommensurate 89/83/71/107-mode chemistry.  The resulting
advected strain widths are predominantly 8--32 px at native output; nothing is
random, tiled, stamped, or added merely as a collision-test texture.

Candidate only; no production wiring.  SPB-WILDS 2026-08-24.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import numpy as np

from .fractured_wilds_petri_independent_w4_2026 import (
    Grammar, S, TAU, i4_amber_plankton,
)
from .fractured_wilds_petri_independent_w5_2026 import _later_standard_map_history


def _micro_lamellar_inoculation(source_x, source_y):
    """Two-strain culture whose fine wavelengths predate the flow.

    All terms are material coordinates.  The later standard-map history moves
    and folds them causally, so the small marks are anatomy rather than an
    image-space detail/noise overlay.
    """
    return (
        np.sin(TAU * (89.0 * source_x
                      + .19 * np.sin(TAU * (3.0 * source_y + .17 * source_x))))
        + .39 * np.cos(TAU * (83.0 * source_y - 5.0 * source_x
                              + .11 * np.sin(TAU * (2.0 * source_x))))
        + .17 * np.sin(TAU * (71.0 * source_x + 73.0 * source_y))
        + .15 * np.sin(TAU * (107.0 * source_x - 89.0 * source_y))
    ).astype(np.float32)


def i7_amber_plankton() -> Grammar:
    return i4_amber_plankton(
        _later_standard_map_history,
        _micro_lamellar_inoculation,
        detail_profile="micro",
        spec_profile="orthogonal_history",
    )


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fpe_amber_plankton": i7_amber_plankton,
}
HUES = {"fpe_amber_plankton": (.09, .51)}
PETRI_IDS = tuple(BUILDERS)


@lru_cache(maxsize=20)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    spec = np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)
    return grammar.paint, spec


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
    metal, rough, coat = (
        spec[:, :, i].astype(np.float32) / 255.0 for i in range(3)
    )
    aperture = np.clip(1.0 - .52 * rough, .22, 1.0)
    la = np.clip(
        .09 + 1.12 * metal * aperture + .35 * owners["A"] - .10 * owners["B"],
        .08,
        1.28,
    )
    lb = np.clip(
        .09 + 1.12 * coat * aperture + .35 * owners["B"] - .10 * owners["A"],
        .08,
        1.28,
    )
    a = np.clip(
        paint * la[..., None]
        + np.asarray((.25, .06, .008), np.float32)
        * (metal * aperture * (.44 + .56 * owners["A"]))[..., None],
        0,
        1,
    )
    b = np.clip(
        paint * lb[..., None]
        + np.asarray((.008, .10, .26), np.float32)
        * (coat * aperture * (.44 + .56 * owners["B"]))[..., None],
        0,
        1,
    )
    return a.astype(np.float32), b.astype(np.float32), np.abs(a - b).astype(np.float32)


__all__ = [
    "BUILDERS",
    "Grammar",
    "HUES",
    "PETRI_IDS",
    "_authored",
    "clear_cache",
    "debug_angle_pair",
    "debug_grammar",
    "debug_hue_null",
    "owner_unions",
]
