# -*- coding: utf-8 -*-
"""Independent Petri I5: later-time repair of I4 Amber Plankton.

I4 is frozen as a non-repeating REPAIR-CANDIDATE whose physical folds were far
too large.  I5 keeps that one reserved process and advances the deterministic
area-preserving flow to a later, stronger mixing state.  It imports the I4
literal chemistry/spec recipe only for this same finish; no other ID shares it.
Candidate only, no production wiring.  SPB-WILDS 2026-08-24.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import numpy as np

from .fractured_wilds_petri_independent_w4_2026 import (
    Grammar, S, TAU, U, V, i4_amber_plankton,
)


def _later_standard_map_history():
    x = U.copy()
    y = V.copy()
    golden = .61803398875
    for step in reversed(range(18)):
        phase_a = np.mod((step + 1) * golden, 1.0)
        phase_b = np.mod((step + 1) * .41421356237, 1.0)
        kx = .151 + .034 * np.sin((step + 1) * 1.173)
        ky = .163 + .031 * np.cos((step + 1) * .937)
        y = np.mod(y - ky * np.sin(TAU * (x + phase_b)), 1.0)
        x = np.mod(x - kx * np.sin(TAU * (y + phase_a)), 1.0)
    return x.astype(np.float32), y.astype(np.float32)


def i5_amber_plankton() -> Grammar:
    return i4_amber_plankton(_later_standard_map_history)


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fpe_amber_plankton": i5_amber_plankton,
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
