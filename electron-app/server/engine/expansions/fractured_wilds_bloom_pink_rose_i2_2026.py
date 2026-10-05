# -*- coding: utf-8 -*-
"""Pink Rose PR-I2: continuous collision-fused Fibonacci lamina.

PR-I1 is frozen as a sparse repeated-petal stamp field.  I2 changes the
representation: 144 enlarged hidden laminae overlap everywhere, chronological
winner/runner-up collisions fuse the crop, and no standalone petal silhouette
or uncovered background is allowed to survive.  Candidate only; unwired.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import numpy as np

from .fractured_wilds_bloom_pink_rose_i1_2026 import (
    GOLDEN_ANGLE, PHI_INV, S, U, V, Grammar, _compose_pink_rose,
)


def _collision_fused_lamina():
    top = np.full((S, S), -1e6, np.float32)
    second = np.full((S, S), -1e6, np.float32)
    win_p = np.zeros((S, S), np.float32)
    win_q = np.zeros((S, S), np.float32)
    win_rho = np.ones((S, S), np.float32)
    win_theta = np.zeros((S, S), np.float32)
    win_age = np.zeros((S, S), np.float32)
    win_index = np.zeros((S, S), np.float32)

    count = 144
    for i in range(count):
        fi = np.float32(i + .5)
        # Hidden Fibonacci chronology spans an expanded crop; the continuous
        # winner field—not the origins—is rendered.
        cx = np.float32(-.18 + 1.36 * np.mod(fi * PHI_INV
                                            + .083 * np.sin(fi * 1.113), 1.0))
        cy = np.float32(-.18 + 1.36 * np.mod(fi * np.float32(.41421356237)
                                            + .071 * np.cos(fi * 1.731), 1.0))
        theta = np.float32(i * GOLDEN_ANGLE + .51 * np.sin(fi * .773))
        ct, st = np.cos(theta), np.sin(theta)
        dx, dy = U - cx, V - cy
        along = dx * ct + dy * st
        across = -dx * st + dy * ct

        length = np.float32(.125 + .060 * (.5 + .5 * np.sin(fi * 1.927)))
        width = np.float32(.071 + .041 * (.5 + .5 * np.cos(fi * 2.311)))
        p = along / length
        curl = np.float32(.17 + .09 * np.sin(fi * .619))
        q = across / width - curl * np.sin(np.pi * (p + .22 * np.sin(fi)))
        taper = np.maximum(.34, 1.0 - .48 * np.power(np.abs(p), 1.35))
        # Each lamina has a different, low-amplitude asymmetric margin.  It is
        # used for collision chronology and never drawn as a repeated outline.
        serration = (.030 + .014 * np.sin(fi * .337)) * np.sin(
            np.float32(2.0 * np.pi) * (2.0 + (i % 4)) * p + fi * .41
        )
        rho = np.square(np.abs(p) + serration) + np.square(q / taper)
        age = np.float32(i / (count - 1))
        score = (1.0 - rho + .018 * age
                 + .024 * np.sin(np.float32(2.0 * np.pi)
                                  * (.73 * p - .57 * q) + fi * .83)).astype(np.float32)

        beats = score > top
        second = np.where(beats, top, np.maximum(second, score))
        top = np.where(beats, score, top)
        win_p = np.where(beats, p, win_p)
        win_q = np.where(beats, q, win_q)
        win_rho = np.where(beats, rho, win_rho)
        win_theta = np.where(beats, theta, win_theta)
        win_age = np.where(beats, age, win_age)
        win_index = np.where(beats, i, win_index)

    return tuple(np.asarray(v, np.float32) for v in (
        top, second, win_p, win_q, win_rho, win_theta, win_age, win_index,
    ))


@lru_cache(maxsize=1)
def i2_pink_rose() -> Grammar:
    return _compose_pink_rose(_collision_fused_lamina, "fused")


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fbl_pink_rose": i2_pink_rose,
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
    i2_pink_rose.cache_clear()


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
