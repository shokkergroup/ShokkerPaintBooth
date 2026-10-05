# -*- coding: utf-8 -*-
"""Pink Rose PR-I4: soft Fibonacci collision-moment lamina.

PR-I1--I3 are frozen as sparse stamps or dense floral shingles.  I4 abandons
discrete winning territories.  Eighty-nine unequal hidden laminae
contribute soft material, orientation, age and anatomy moments everywhere;
only their fused collision history is rendered.  No individual petal boundary
can close, and no seed/point census is painted.  Candidate only; unwired.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np


S = 512
TAU = np.float32(2.0 * np.pi)
GA = np.float32(np.pi * (3.0 - np.sqrt(5.0)))
PHI_INV = np.float32((np.sqrt(5.0) - 1.0) * .5)
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
U = (xx + .5) / S
V = (yy + .5) / S


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    hue_null: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]


def _f(value):
    return np.clip(np.asarray(value, np.float32), 0.0, 1.0)


def _n(value):
    value = np.asarray(value, np.float32)
    lo = float(np.percentile(value, .5))
    hi = float(np.percentile(value, 99.5))
    return _f((value - lo) / max(hi - lo, 1e-6))


def _soft_gt(value, threshold, width):
    return _f(.5 + .5 * np.tanh((np.asarray(value, np.float32) - threshold)
                                / max(width, 1e-5)))


def _rgb(code):
    code = code.lstrip("#")
    return np.asarray([int(code[i:i + 2], 16) / 255.0 for i in (0, 2, 4)],
                      np.float32)


def _blend(base, color, mask):
    mask = _f(mask)[..., None]
    return base * (1.0 - mask) + np.asarray(color, np.float32) * mask


def _palette(field, colors):
    field = _f(field) * np.float32(len(colors) - 1)
    low = np.floor(field).astype(np.int32)
    high = np.minimum(low + 1, len(colors) - 1)
    mix = (field - low)[..., None]
    bank = np.asarray(colors, np.float32)
    return bank[low] * (1.0 - mix) + bank[high] * mix


def _soft_meristem_moments():
    zeros = lambda: np.zeros((S, S), np.float32)
    sum_w = zeros()
    sum_w2 = zeros()
    sum_age = zeros()
    sum_lineage = zeros()
    sum_c2 = zeros()
    sum_s2 = zeros()
    midrib = zeros()
    veins = zeros()
    margins = zeros()
    dew = zeros()
    stamens = zeros()
    sepals = zeros()

    # 89 is itself a Fibonacci number and is dense enough for continuous soft
    # fusion while keeping the cold authored render inside the 2-3 s budget.
    count = 89
    for i in range(count):
        fi = np.float32(i + .5)
        cx = np.float32(-.16 + 1.32 * np.mod(fi * PHI_INV
                                            + .079 * np.sin(fi * 1.113), 1.0))
        cy = np.float32(-.16 + 1.32 * np.mod(fi * np.float32(.41421356237)
                                            + .067 * np.cos(fi * 1.731), 1.0))
        theta = np.float32(i * GA + .49 * np.sin(fi * .773))
        ct, st = np.cos(theta), np.sin(theta)
        dx, dy = U - cx, V - cy
        along = dx * ct + dy * st
        across = -dx * st + dy * ct
        length = np.float32(.118 + .061 * (.5 + .5 * np.sin(fi * 1.927)))
        width = np.float32(.063 + .042 * (.5 + .5 * np.cos(fi * 2.311)))
        p = along / length
        q = across / width - (.15 + .08 * np.sin(fi * .619)) * np.sin(
            np.pi * (p + .19 * np.sin(fi))
        )
        taper = np.maximum(.34, 1.0 - .49 * np.power(np.abs(p), 1.38))
        rho = np.square(p) + np.square(q / taper)
        weight = np.exp(-1.86 * rho).astype(np.float32)
        age = np.float32(i / (count - 1))
        lineage = np.float32(np.sin(fi * GA * .731 + fi * .113))

        sum_w += weight
        sum_w2 += weight * weight
        sum_age += weight * age
        sum_lineage += weight * lineage
        sum_c2 += weight * np.cos(2.0 * theta)
        sum_s2 += weight * np.sin(2.0 * theta)

        # Fine anatomy is accumulated into one tissue field.  Selection is by
        # chronology, so these are unequal event families rather than one kit
        # stamped into every lamina.
        # Scalar chronology gates are resolved before allocating raster math.
        # The earlier version multiplied six expensive rasters by nearly-zero
        # scalar masks for every lamina and took 6.6 s cold.  Skipping excluded
        # physical families changes no placement rule and adds no approximation.
        if float(np.sin(fi * 1.613)) > .48:
            midrib += weight * np.exp(-np.square(q / .068)) \
                * np.exp(-np.power(np.abs(p) / .82, 8.0))

        if float(np.cos(fi * 1.271)) > .44:
            branch_phase = np.abs(np.sin(TAU * (2.17 * p + .61 * np.abs(q))
                                         + fi * .319))
            veins += weight * _soft_gt(branch_phase, .925, .026) \
                * _soft_gt(np.abs(q), .16, .06) \
                * np.exp(-np.power(np.abs(p) / .90, 8.0))

        if float(np.sin(fi * 1.791)) > .31:
            margins += weight * np.exp(
                -np.square((np.sqrt(np.maximum(rho, 0.0)) - .82) / .060)
            )

        if float(np.sin(fi * 2.071)) > .68:
            dew_r = np.hypot(p - (.17 + .11 * np.sin(fi * .217)),
                             q - .16 * np.cos(fi * .311))
            dew += weight * np.exp(-np.square((dew_r - .13) / .038))

        if float(np.cos(fi * 1.433)) > .58:
            stamen_r = np.hypot(p + .39, q * 1.20)
            stamens += weight * _soft_gt(q, -.08, .06) \
                * np.exp(-np.square((stamen_r - .35) / .044))

        if float(np.sin(fi * 1.121)) > .64:
            sepals += weight * _soft_gt(-p, .50, .07) \
                * _soft_gt(np.sin(fi + 5.3 * q), .70, .09)

    safe = np.maximum(sum_w, 1e-6)
    age_field = _f(sum_age / safe)
    lineage_field = np.clip(sum_lineage / safe, -1.0, 1.0).astype(np.float32)
    c2, s2 = sum_c2 / safe, sum_s2 / safe
    coherence = _f(np.hypot(c2, s2))
    orientation = (.5 * np.arctan2(s2, c2)).astype(np.float32)
    participation = _n(safe * safe / np.maximum(sum_w2, 1e-6))
    disorder = _f(1.0 - coherence)
    return {
        "age": age_field,
        "lineage": lineage_field,
        "orientation": orientation,
        "participation": participation,
        "disorder": disorder,
        "midrib": _n(midrib / safe),
        "veins": _n(veins / safe),
        "margins": _n(margins / safe),
        "dew": _n(dew / safe),
        "stamens": _n(stamens / safe),
        "sepals": _n(sepals / safe),
    }


def _compose_soft_meristem(detail_profile="base") -> Grammar:
    f = _soft_meristem_moments()
    age = f["age"]
    lineage = f["lineage"]
    orientation = f["orientation"]
    participation = f["participation"]
    disorder = f["disorder"]
    repair_profile = detail_profile == "causal_detail"

    if repair_profile:
        # PR-I5: ownership is still a fused moment of the same tissue, but the
        # higher-order collision/orientation term prevents I4's giant vertical
        # material panels without inventing image-space texture.
        ownership = np.tanh(
            1.48 * lineage
            + .72 * np.sin(4.0 * orientation
                           + TAU * (2.8 * age + 1.7 * participation))
            + .31 * np.cos(TAU * (1.9 * age - .8 * disorder))
        )
    else:
        ownership = np.tanh(2.15 * lineage
                            + .48 * np.sin(2.0 * orientation + TAU * age))
    lamina_a = _soft_gt(ownership, .055, .17)
    lamina_b = _soft_gt(-ownership, .055, .17)

    collision_core = _f(
        _soft_gt(participation, .48, .11)
        * _soft_gt(disorder, .20, .09)
    )
    broken_collision = _soft_gt(
        np.sin(TAU * (3.7 * age + 1.1 * lineage) + 2.0 * orientation), .24, .17
    )
    collision_underfolds = _f(
        collision_core * broken_collision * (.22 + .78 * f["margins"])
    )
    if repair_profile:
        collision_underfolds = _f(
            _soft_gt(collision_underfolds, .105, .060)
            * _soft_gt(f["margins"], .075, .055)
        )

    redirected_midribs = _f(
        f["midrib"] * (.26 + .74 * disorder)
        * _soft_gt(np.sin(TAU * (2.3 * age - lineage)), -.10, .16)
    )
    secondary_veins = _f(
        f["veins"] * (.24 + .76 * participation)
        * _soft_gt(np.cos(TAU * (1.7 * age + .6 * lineage)), .02, .18)
    )
    curled_margins = _f(
        f["margins"] * _soft_gt(participation, .36, .12)
        * _soft_gt(np.cos(3.0 * orientation + TAU * age), .08, .18)
    )
    if repair_profile:
        redirected_midribs = _f(
            _soft_gt(f["midrib"], .17, .055)
            * _soft_gt(disorder, .12, .075)
            * _soft_gt(np.sin(TAU * (2.3 * age - lineage)), -.10, .16)
        )
        secondary_veins = _f(
            _soft_gt(f["veins"], .22, .060)
            * _soft_gt(participation, .20, .09)
            * _soft_gt(np.cos(TAU * (1.7 * age + .6 * lineage)), -.08, .16)
        )
        curled_margins = _f(
            _soft_gt(f["margins"], .20, .060)
            * _soft_gt(participation, .24, .10)
            * _soft_gt(np.cos(3.0 * orientation + TAU * age), -.02, .16)
        )

    gy_o, gx_o = np.gradient(orientation)
    gy_l, gx_l = np.gradient(lineage)
    defect = _n(np.hypot(gx_o, gy_o) + .65 * np.hypot(gx_l, gy_l))
    tear_phase = np.abs(np.sin(TAU * (5.0 * U - 3.0 * V + 1.7 * age)))
    tear_lips = _f(
        _soft_gt(defect, .66, .10) * _soft_gt(tear_phase, .88, .035)
        * (.25 + .75 * collision_core)
    )
    if repair_profile:
        tear_lips = _f(
            _soft_gt(defect, .48, .075) * _soft_gt(tear_phase, .79, .045)
            * (.22 + .78 * _soft_gt(collision_core, .18, .09))
        )

    dew_cups = _f(
        f["dew"] * _soft_gt(participation, .46, .12)
        * _soft_gt(np.sin(TAU * (age + lineage)), .18, .17)
    )
    stamen_arcs = _f(
        f["stamens"] * _soft_gt(disorder, .16, .10)
        * _soft_gt(np.cos(TAU * (age * 1.3 - lineage)), -.05, .18)
    )
    negative_slits = _f(
        _soft_gt(disorder, .48, .09) * _soft_gt(defect, .54, .10)
        * _soft_gt(np.sin(TAU * (7.0 * U + 4.0 * V) + orientation), .76, .08)
    )
    sepal_hooks = _f(
        f["sepals"] * _soft_gt(1.0 - age, .54, .12)
        * _soft_gt(np.sin(3.0 * orientation - TAU * lineage), .20, .17)
    )
    if repair_profile:
        dew_cups = _f(
            _soft_gt(f["dew"], .22, .065)
            * _soft_gt(participation, .27, .10)
            * _soft_gt(np.sin(TAU * (age + lineage)), .03, .16)
        )
        stamen_arcs = _f(
            _soft_gt(f["stamens"], .20, .060)
            * _soft_gt(disorder, .10, .08)
            * _soft_gt(np.cos(TAU * (age * 1.3 - lineage)), -.17, .16)
        )
        negative_slits = _f(
            _soft_gt(disorder, .36, .075) * _soft_gt(defect, .40, .075)
            * _soft_gt(np.sin(TAU * (7.0 * U + 4.0 * V) + orientation), .62, .075)
        )
        sepal_hooks = _f(
            _soft_gt(f["sepals"], .17, .060)
            * _soft_gt(1.0 - age, .43, .10)
            * _soft_gt(np.sin(3.0 * orientation - TAU * lineage), .02, .16)
        )

    masks = {
        "fused_lamina_A": lamina_a,
        "fused_lamina_B": lamina_b,
        "collision_underfolds": collision_underfolds,
        "redirected_midribs": redirected_midribs,
        "secondary_veins": secondary_veins,
        "curled_margins": curled_margins,
        "tear_lips": tear_lips,
        "dew_cups": dew_cups,
        "stamen_arcs": stamen_arcs,
        "negative_slits": negative_slits,
        "sepal_hooks": sepal_hooks,
    }
    banks = {
        "fused_lamina_A": "A", "fused_lamina_B": "B",
        "collision_underfolds": "B", "redirected_midribs": "A",
        "secondary_veins": "B", "curled_margins": "A",
        "tear_lips": "B", "dew_cups": "A", "stamen_arcs": "A",
        "negative_slits": "B", "sepal_hooks": "B",
    }

    rose_bank = [_rgb(c) for c in (
        "#240812", "#3d0b19", "#5a1024", "#79172f", "#98233c", "#b7334d",
        "#d14963", "#e8667c", "#f28596", "#f9a8b4", "#ffc9d0", "#ffe7e8",
    )]
    violet_bank = [_rgb(c) for c in (
        "#12081f", "#221032", "#351747", "#4a205d", "#612b75", "#79398e",
        "#924ba6", "#ab61bd", "#c37bd0", "#d99adf", "#eabbe9", "#f8dcf4",
    )]
    tone = _f(.44 * age + .26 * participation + .18 * _n(np.cos(orientation))
              + .12 * (1.0 - disorder))
    if repair_profile:
        tone = _f(.34 * tone + .26 * age + .22 * participation
                  + .18 * _n(lineage * np.cos(2.0 * orientation)))
    color_a = _palette(tone, rose_bank)
    color_b = _palette(1.0 - .65 * tone + .20 * disorder, violet_bank)
    total = np.maximum(lamina_a + lamina_b, 1e-5)
    wa, wb = lamina_a / total, lamina_b / total
    paint = color_a * wa[..., None] + color_b * wb[..., None]
    paint = _blend(paint, _rgb("#4d1232"), .52 * collision_underfolds)
    paint = _blend(paint, _rgb("#ffd4dc"), .84 * redirected_midribs)
    paint = _blend(paint, _rgb("#ff7895"), .74 * secondary_veins)
    paint = _blend(paint, _rgb("#ffb6c6"), .78 * curled_margins)
    paint = _blend(paint, _rgb("#641027"), .92 * tear_lips)
    paint = _blend(paint, _rgb("#bcefff"), .94 * dew_cups)
    paint = _blend(paint, _rgb("#ffd34e"), .94 * stamen_arcs)
    paint = _blend(paint, _rgb("#090309"), .99 * negative_slits)
    paint = _blend(paint, _rgb("#88c957"), .82 * sepal_hooks)

    hue_null = .30 * lamina_a + .56 * lamina_b
    for name, level in (
        ("collision_underfolds", .15), ("redirected_midribs", .92),
        ("secondary_veins", .70), ("curled_margins", .82),
        ("tear_lips", .10), ("dew_cups", .98), ("stamen_arcs", .88),
        ("negative_slits", .02), ("sepal_hooks", .62),
    ):
        hue_null = hue_null * (1.0 - masks[name]) + level * masks[name]
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    vascular_anisotropy = _f(.5 + .5 * np.sin(
        TAU * (4.2 * age + 1.7 * lineage) + 2.0 * orientation
    ))
    metal_field = _f(
        .05 + .51 * redirected_midribs + .34 * secondary_veins
        + .28 * stamen_arcs + .20 * sepal_hooks
        + .16 * lamina_a * vascular_anisotropy - .15 * negative_slits
    )
    rough_field = _f(
        .17 + .48 * lamina_b * (.24 + .76 * (1.0 - age))
        + .34 * collision_underfolds + .30 * tear_lips
        + .21 * disorder + .17 * negative_slits
        - .29 * dew_cups - .17 * redirected_midribs
    )
    moisture = _f(.5 + .5 * np.cos(
        TAU * (2.5 * age - 1.4 * lineage) - orientation
    ))
    coat_field = _f(
        .04 + .59 * dew_cups + .38 * curled_margins + .30 * stamen_arcs
        + .25 * lamina_a * moisture + .18 * secondary_veins
        - .22 * tear_lips - .17 * negative_slits
    )
    metal = np.clip(7.0 + 247.0 * metal_field, 0, 255).astype(np.float32)
    rough = np.clip(15.0 + 233.0 * rough_field, 0, 255).astype(np.float32)
    coat = np.clip(5.0 + 249.0 * coat_field, 0, 255).astype(np.float32)

    marks = tuple((name, _f(mask), banks[name]) for name, mask in masks.items())
    flat = [name for name, mask, _owner in marks if float(mask.std()) < .0015]
    if flat:
        raise ValueError(f"Pink Rose I4 has flat causal families: {flat}")
    return Grammar(marks, _f(paint), _f(hue_null), (metal, rough, coat))


@lru_cache(maxsize=1)
def i4_pink_rose() -> Grammar:
    return _compose_soft_meristem("base")


BUILDERS: Mapping[str, Callable[[], Grammar]] = {"fbl_pink_rose": i4_pink_rose}
HUES = {"fbl_pink_rose": (.97, .82)}
BLOOM_IDS = tuple(BUILDERS)


@lru_cache(maxsize=4)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    spec = np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)
    return grammar.paint, spec


def clear_cache():
    _authored.cache_clear()
    i4_pink_rose.cache_clear()


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
    a = np.clip(paint * la[..., None]
                + np.asarray((.25, .035, .055), np.float32)
                * (metal * aperture * (.42 + .58 * owners["A"]))[..., None], 0, 1)
    b = np.clip(paint * lb[..., None]
                + np.asarray((.045, .03, .25), np.float32)
                * (coat * aperture * (.42 + .58 * owners["B"]))[..., None], 0, 1)
    return a.astype(np.float32), b.astype(np.float32), np.abs(a - b).astype(np.float32)


__all__ = [
    "BLOOM_IDS", "BUILDERS", "Grammar", "HUES", "_authored", "clear_cache",
    "debug_angle_pair", "debug_grammar", "debug_hue_null", "owner_unions",
    "_compose_soft_meristem",
]
