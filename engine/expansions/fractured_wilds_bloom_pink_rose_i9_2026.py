# -*- coding: utf-8 -*-
"""Pink Rose PR-I9: fully fused fine-cluster meristem.

I8 exposed its 144 causal clusters as repeated isolated specimens.  I9 raises
the hidden Fibonacci territory chronology to 377 smaller, more overlapping
clusters.  Every deposited primitive remains an open 8--32 px micro-lamina;
larger tissue exists only as fusion of those fine events.  No random/noise,
macro petal primitive, closed stamp, paver, hub, row/grid, or long carrier.

Isolated candidate only; NOT owner accepted and deliberately unwired.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import numpy as np

from .fractured_wilds_bloom_pink_rose_i4_2026 import (
    S, Grammar, _blend, _f, _n, _palette, _rgb,
)
from .fractured_wilds_bloom_pink_rose_i8_2026 import _clustered_tissue


@lru_cache(maxsize=1)
def i9_pink_rose() -> Grammar:
    (masks, support_a, support_b, support_all, ridge, shade_tone,
     owner_mix, overlap, defect, _meta) = _clustered_tissue("fused")
    rose_bank = [_rgb(c) for c in (
        "#240711", "#3d0b1b", "#5b1127", "#791934", "#982442",
        "#b63553", "#d04a66", "#e8667e", "#f48799", "#faaeba",
        "#ffd0d5", "#ffe9e9",
    )]
    violet_bank = [_rgb(c) for c in (
        "#10071d", "#20102e", "#341642", "#491f57", "#60296e",
        "#773785", "#90479c", "#a95bb4", "#c175ca", "#d796dc",
        "#e8b8e9", "#f7daf4",
    )]
    # Fine support/shade accumulation is kept visibly dominant.  No closed
    # territory boundary is rendered or thresholded.
    tone_a = _f(.16 + .50 * shade_tone + .22 * ridge + .12 * overlap)
    tone_b = _f(.15 + .47 * (1.0 - shade_tone) + .23 * defect
                + .15 * support_all)
    color_a = _palette(tone_a, rose_bank)
    color_b = _palette(tone_b, violet_bank)
    paint = color_a * owner_mix[..., None] + color_b * (1.0 - owner_mix)[..., None]
    paint = _blend(paint, _rgb("#ff9db0"), .31 * ridge * support_a)
    paint = _blend(paint, _rgb("#67204f"), .26 * ridge * support_b)
    paint = _blend(paint, _rgb("#4b102f"), .69 * masks["collision_underfolds"])
    paint = _blend(paint, _rgb("#ffd9df"), .84 * masks["redirected_midribs"])
    paint = _blend(paint, _rgb("#ff7593"), .76 * masks["secondary_veins"])
    paint = _blend(paint, _rgb("#ffb7cb"), .78 * masks["curled_margins"])
    paint = _blend(paint, _rgb("#651027"), .91 * masks["tear_lips"])
    paint = _blend(paint, _rgb("#bcefff"), .91 * masks["dew_cups"])
    paint = _blend(paint, _rgb("#ffd447"), .91 * masks["stamen_arcs"])
    paint = _blend(paint, _rgb("#070208"), .985 * masks["negative_slits"])
    paint = _blend(paint, _rgb("#88c85a"), .82 * masks["sepal_hooks"])

    hue_null = _f(.29 * owner_mix + .57 * (1.0 - owner_mix)
                  + .08 * shade_tone + .06 * ridge)
    for name, level in (
        ("collision_underfolds", .13), ("redirected_midribs", .94),
        ("secondary_veins", .72), ("curled_margins", .84),
        ("tear_lips", .09), ("dew_cups", .99), ("stamen_arcs", .89),
        ("negative_slits", .015), ("sepal_hooks", .64),
    ):
        hue_null = hue_null * (1.0 - masks[name]) + level * masks[name]
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    vascular = _n(
        masks["redirected_midribs"] + .70 * masks["secondary_veins"]
        + .46 * masks["stamen_arcs"] + .29 * ridge * support_a
    )
    fracture = _n(
        masks["collision_underfolds"] + .80 * masks["tear_lips"]
        + .50 * masks["negative_slits"] + .31 * defect * support_b
    )
    wetness = _n(
        masks["dew_cups"] + .74 * masks["curled_margins"]
        + .42 * masks["stamen_arcs"] + .27 * overlap * support_a
        - .29 * masks["tear_lips"]
    )
    metal = np.clip(6.0 + 248.0 * _f(.04 + .89 * vascular), 0, 255)
    rough = np.clip(13.0 + 235.0 * _f(.09 + .82 * fracture), 0, 255)
    coat = np.clip(4.0 + 250.0 * _f(.035 + .92 * wetness), 0, 255)

    banks = {
        "micro_lamina_A": "A", "micro_lamina_B": "B",
        "collision_underfolds": "B", "redirected_midribs": "A",
        "secondary_veins": "B", "curled_margins": "A",
        "tear_lips": "B", "dew_cups": "A", "stamen_arcs": "A",
        "negative_slits": "B", "sepal_hooks": "B",
    }
    marks = tuple((name, _f(mask), banks[name]) for name, mask in masks.items())
    flat = [name for name, mask, _owner in marks if float(mask.std()) < .0015]
    if flat:
        raise ValueError(f"Pink Rose I9 has flat causal families: {flat}")
    return Grammar(
        marks, _f(paint), _f(hue_null),
        (metal.astype(np.float32), rough.astype(np.float32), coat.astype(np.float32)),
    )


BUILDERS: Mapping[str, Callable[[], Grammar]] = {"fbl_pink_rose": i9_pink_rose}
HUES = {"fbl_pink_rose": (.97, .82)}
BLOOM_IDS = tuple(BUILDERS)


@lru_cache(maxsize=4)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    spec = np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)
    return grammar.paint, spec


def clear_cache():
    _authored.cache_clear()
    i9_pink_rose.cache_clear()
    _clustered_tissue.cache_clear()


def debug_grammar(fid: str):
    return BUILDERS[fid]()


def debug_hue_null(fid: str):
    return debug_grammar(fid).hue_null


def debug_primary_measurements(fid: str = "fbl_pink_rose"):
    if fid not in BUILDERS:
        raise KeyError(fid)
    return _clustered_tissue("fused")[-1]


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
    aperture = np.clip(1.0 - .48 * rough, .23, 1.0)
    la = np.clip(.09 + 1.06 * metal * aperture + .38 * owners["A"]
                 - .10 * owners["B"], .07, 1.30)
    lb = np.clip(.09 + 1.06 * coat * aperture + .38 * owners["B"]
                 - .10 * owners["A"], .07, 1.30)
    a = np.clip(
        paint * la[..., None]
        + np.asarray((.26, .035, .055), np.float32)
        * (metal * aperture * (.40 + .60 * owners["A"]))[..., None], 0, 1,
    )
    b = np.clip(
        paint * lb[..., None]
        + np.asarray((.045, .03, .26), np.float32)
        * (coat * aperture * (.40 + .60 * owners["B"]))[..., None], 0, 1,
    )
    return a.astype(np.float32), b.astype(np.float32), np.abs(a - b).astype(np.float32)


__all__ = [
    "BLOOM_IDS", "BUILDERS", "Grammar", "HUES", "_authored", "clear_cache",
    "debug_angle_pair", "debug_grammar", "debug_hue_null",
    "debug_primary_measurements", "owner_unions",
]
