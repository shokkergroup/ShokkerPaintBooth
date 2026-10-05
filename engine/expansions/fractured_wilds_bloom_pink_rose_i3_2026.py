# -*- coding: utf-8 -*-
"""Pink Rose PR-I3: interdigitated collision-fused lamina.

PR-I2's full crop still read as repeated decorated leaf shingles.  I3 keeps the
continuous overlapping chronology but fuses A/B color through collisions and
permits midribs/secondary veins on mutually exclusive minority territories.
Complete petal silhouettes are not painted.  Candidate only; unwired.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import numpy as np

from .fractured_wilds_bloom_pink_rose_i1_2026 import (
    S, Grammar, _compose_pink_rose,
)
from .fractured_wilds_bloom_pink_rose_i2_2026 import _collision_fused_lamina


@lru_cache(maxsize=1)
def i3_pink_rose() -> Grammar:
    return _compose_pink_rose(_collision_fused_lamina, "interdigitated")


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fbl_pink_rose": i3_pink_rose,
}
HUES = {"fbl_pink_rose": (.97, .82)}
BLOOM_IDS = tuple(BUILDERS)


@lru_cache(maxsize=4)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    spec = np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)
    return grammar.paint, spec


def clear_cache():
    _authored.cache_clear()
    i3_pink_rose.cache_clear()


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
    aperture = np.clip(1.0 - .50 * rough, .22, 1.0)
    la = np.clip(.10 + 1.08 * metal * aperture + .36 * owners["A"]
                 - .09 * owners["B"], .08, 1.30)
    lb = np.clip(.10 + 1.08 * coat * aperture + .36 * owners["B"]
                 - .09 * owners["A"], .08, 1.30)
    a = np.clip(
        paint * la[..., None]
        + np.asarray((.25, .035, .055), np.float32)
        * (metal * aperture * (.42 + .58 * owners["A"]))[..., None], 0, 1,
    )
    b = np.clip(
        paint * lb[..., None]
        + np.asarray((.045, .03, .25), np.float32)
        * (coat * aperture * (.42 + .58 * owners["B"]))[..., None], 0, 1,
    )
    return a.astype(np.float32), b.astype(np.float32), np.abs(a - b).astype(np.float32)


__all__ = [
    "BLOOM_IDS", "BUILDERS", "Grammar", "HUES", "_authored", "clear_cache",
    "debug_angle_pair", "debug_grammar", "debug_hue_null", "owner_unions",
]
