# -*- coding: utf-8 -*-
"""Isolated Bloom Pink Rose PR-I1: overlapping Fibonacci meristem tissue.

SPB-WILDS Pink Rose I1, 2026-08-24.  W4's giant rosette/empty centre is
retired.  This candidate grows 144 unequal, chronologically overlapping petal
territories from an expanded crop using a golden-angle meristem chronology.
The seed census is never painted: only exposed lamina, collision underfolds,
redirected veins, tears, dew cups, stamen arcs and negative slits survive.

No RNG/noise, grid, row, paver, repeated stamp bank, central hub, long carrier
path or production wiring is used.  Candidate evidence only; not owner accepted.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np


S = 512
TAU = np.float32(2.0 * np.pi)
GOLDEN_ANGLE = np.float32(np.pi * (3.0 - np.sqrt(5.0)))
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


def _tiered(field, colors):
    thresholds = np.linspace(.06, .94, len(colors) - 1, dtype=np.float32)
    index = np.digitize(_f(field), thresholds)
    return np.asarray(colors, np.float32)[index]


def _palette_lerp(field, colors):
    field = _f(field) * np.float32(len(colors) - 1)
    low = np.floor(field).astype(np.int32)
    high = np.minimum(low + 1, len(colors) - 1)
    mix = (field - low)[..., None]
    bank = np.asarray(colors, np.float32)
    return bank[low] * (1.0 - mix) + bank[high] * mix


def _petal_tissue():
    """Return the top two chronological laminae and winner-local coordinates."""
    top = np.full((S, S), -1e6, np.float32)
    second = np.full((S, S), -1e6, np.float32)
    win_p = np.zeros((S, S), np.float32)
    win_q = np.zeros((S, S), np.float32)
    win_rho = np.ones((S, S), np.float32)
    win_theta = np.zeros((S, S), np.float32)
    win_age = np.zeros((S, S), np.float32)
    win_index = np.zeros((S, S), np.float32)

    # Fibonacci chronology distributes *hidden* growth origins through an
    # expanded crop.  Individual SDFs are unequal and mutually occluding; no
    # seed dot, repeated petal stamp, shared centre, or universal rim is drawn.
    count = 144
    for i in range(count):
        fi = np.float32(i + .5)
        cx = np.float32(-.13 + 1.26 * np.mod(fi * PHI_INV + .071 * np.sin(fi * 1.113), 1.0))
        cy = np.float32(-.13 + 1.26 * np.mod(fi * np.float32(.41421356237)
                                            + .063 * np.cos(fi * 1.731), 1.0))
        theta = np.float32(i * GOLDEN_ANGLE + .43 * np.sin(fi * .773))
        ct, st = np.cos(theta), np.sin(theta)
        dx, dy = U - cx, V - cy
        along = dx * ct + dy * st
        across = -dx * st + dy * ct

        length = np.float32(.070 + .039 * (.5 + .5 * np.sin(fi * 1.927)))
        width = np.float32(.028 + .019 * (.5 + .5 * np.cos(fi * 2.311)))
        p = along / length
        curl = np.float32(.13 + .07 * np.sin(fi * .619))
        q = across / width - curl * np.sin(np.pi * (p + .22 * np.sin(fi)))
        taper = np.maximum(.30, 1.0 - .57 * np.power(np.abs(p), 1.45))
        serration = .045 * np.sin(TAU * (2.0 + (i % 5)) * p + fi * .41)
        rho = np.square(np.abs(p) + serration) + np.square(q / taper)
        age = np.float32(i / (count - 1))
        score = (1.0 - rho + .055 * age
                 + .032 * np.sin(TAU * (.9 * p - .7 * q) + fi * .83)).astype(np.float32)

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


def _compose_pink_rose(tissue_fn, tissue_profile="sparse") -> Grammar:
    top, second, p, q, rho, theta, age, index = tissue_fn()
    interdigitated_profile = tissue_profile == "interdigitated"
    fused_profile = tissue_profile in ("fused", "interdigitated")
    covered = (np.ones((S, S), np.float32) if fused_profile
               else _soft_gt(top, -.04, .055))
    overlap = _soft_gt(second, -.09, .055)
    collision_gap = top - second
    collision = _f(covered * overlap * np.exp(-np.square(collision_gap / .085)))

    # A/B ownership follows exposed face handedness and chronology, not palette
    # alternation by seed index.  This keeps the meristem from reading as a
    # coloured cell census while preserving two literal material populations.
    handed = np.sin(theta + 1.17 * p - .61 * q + age * TAU)
    face_a = _f(covered * _soft_gt(handed, .08, .18))
    face_b = _f(covered * _soft_gt(-handed, .08, .18))
    if interdigitated_profile:
        # PR-I3: collision fusion mixes exposed face ownership across winner
        # boundaries.  No territory may advertise a closed, two-tone petal.
        face_a = cv2.GaussianBlur(face_a, (0, 0), 3.2)
        face_b = cv2.GaussianBlur(face_b, (0, 0), 3.2)
        face_total = np.maximum(face_a + face_b, 1e-5)
        face_a = _f(covered * face_a / face_total)
        face_b = _f(covered * face_b / face_total)

    underfold_select = _soft_gt(
        np.sin(index * np.float32(1.317) + 2.4 * p - 1.3 * q),
        .54 if fused_profile else .12,
        .16 if fused_profile else .19,
    )
    collision_underfolds = _f(collision * underfold_select)

    # A petal's short midrib is redirected by the nearest overlap rather than
    # continuing as a crop-spanning rail.
    redirect = .18 * collision * np.sin(theta + index * .37)
    midrib_distance = np.abs(q - redirect * np.sin(np.pi * (p + .5)))
    redirected_midribs = _f(
        covered * _soft_gt(.070 - midrib_distance, 0.0, .016)
        * _soft_gt(.88 - np.abs(p), 0.0, .055)
    )
    if interdigitated_profile:
        redirected_midribs *= _soft_gt(
            np.sin(index * 1.613 + theta), .53, .11
        )

    branch_phase = np.abs(
        np.sin(TAU * (2.1 * p + .58 * np.abs(q) + index * .031))
    )
    secondary_veins = _f(
        covered * _soft_gt(branch_phase, .91, .035)
        * _soft_gt(np.abs(q), .20, .08)
        * _soft_gt(.93 - np.abs(p), 0.0, .06)
    )
    if interdigitated_profile:
        secondary_veins *= _soft_gt(
            np.cos(index * 1.271 - theta), .46, .12
        )

    curl_select = _soft_gt(np.cos(index * 1.791 + 3.0 * p), .34, .16)
    curled_margins = _f(
        covered * curl_select
        * np.exp(-np.square((np.sqrt(np.maximum(rho, 0.0)) - .82) / .075))
    )

    stress = collision * _soft_gt(np.abs(np.sin(theta + index * .53)), .46, .15)
    tear_axis = np.abs(q - .34 * np.sin(3.2 * p + index * .27))
    tear_lips = _f(
        stress * _soft_gt(.13 - tear_axis, 0.0, .025)
        * _soft_gt(np.abs(p), .28, .10)
    )

    # Dew nucleates only in age-selected collision pockets.  Unequal annuli are
    # causal overlap events, sparse and subordinate—not a repeated dot field.
    dew_x = p - (.18 + .14 * np.sin(index * .217))
    dew_y = q - (.18 * np.cos(index * .311))
    dew_radius = .12 + .045 * (.5 + .5 * np.sin(index * .619))
    dew_d = np.hypot(dew_x, dew_y)
    dew_select = _soft_gt(
        np.sin(index * 2.071), .60 if fused_profile else .77, .08
    )
    dew_cups = _f(
        collision * dew_select
        * np.exp(-np.square((dew_d - dew_radius) / .036))
    )

    stamen_radius = np.hypot(p + .42, q * 1.18)
    stamen_select = _soft_gt(np.cos(index * 1.433), .58, .12)
    stamen_arcs = _f(
        covered * stamen_select * _soft_gt(q, -.05, .07)
        * np.exp(-np.square((stamen_radius - .38) / .045))
    )

    slit_select = _soft_gt(np.sin(index * .997 + theta), .67, .10)
    slit_axis = np.abs(q + .16 * np.sin(4.1 * p + index * .19))
    negative_slits = _f(
        covered * slit_select * _soft_gt(.075 - slit_axis, 0.0, .018)
        * _soft_gt(np.abs(p), .35, .08)
    )

    sepal_hooks = _f(
        covered * _soft_gt(-p, .54, .08)
        * _soft_gt(np.sin(index * 1.121 + 5.0 * q), .72, .10)
    )

    masks = {
        "exposed_petal_A": face_a,
        "exposed_petal_B": face_b,
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
        "exposed_petal_A": "A",
        "exposed_petal_B": "B",
        "collision_underfolds": "B",
        "redirected_midribs": "A",
        "secondary_veins": "B",
        "curled_margins": "A",
        "tear_lips": "B",
        "dew_cups": "A",
        "stamen_arcs": "A",
        "negative_slits": "B",
        "sepal_hooks": "B",
    }

    rose_bank = [_rgb(c) for c in (
        "#260912", "#430b1a", "#641127", "#861b35", "#a92c47", "#c8435e",
        "#df6179", "#ef8296", "#f7a3b1", "#ffc2cb", "#ffdde2", "#fff0ef",
    )]
    violet_bank = [_rgb(c) for c in (
        "#160a24", "#28103b", "#3d1855", "#58226e", "#74308a", "#9143a3",
        "#ad5cbb", "#c779d0", "#db99df", "#ebb9eb", "#f6d7f4", "#fff0fb",
    )]
    tissue_tone = _n(
        .42 * age + .24 * _n(np.cos(theta - .7 * p))
        + .20 * _n(1.0 - rho) + .14 * _n(collision_gap)
    )
    if interdigitated_profile:
        tissue_tone = _f(cv2.GaussianBlur(tissue_tone, (0, 0), 2.4))
        color_a = _palette_lerp(tissue_tone, rose_bank)
        color_b = _palette_lerp(
            1.0 - .62 * tissue_tone + .18 * _n(q), violet_bank
        )
    else:
        color_a = _tiered(tissue_tone, rose_bank)
        color_b = _tiered(1.0 - .62 * tissue_tone + .18 * _n(q), violet_bank)
    paint = np.broadcast_to(_rgb("#120710"), (S, S, 3)).copy()
    paint = paint * (1.0 - .91 * covered[..., None])
    paint += color_a * (.83 * face_a)[..., None]
    paint += color_b * (.83 * face_b)[..., None]
    paint = _blend(paint, _rgb("#48112f"), .48 * collision_underfolds)
    paint = _blend(paint, _rgb("#ffd1d7"), .86 * redirected_midribs)
    paint = _blend(paint, _rgb("#ff7894"), .72 * secondary_veins)
    paint = _blend(paint, _rgb("#ffb8c6"), .81 * curled_margins)
    paint = _blend(paint, _rgb("#641027"), .91 * tear_lips)
    paint = _blend(paint, _rgb("#b8eeff"), .92 * dew_cups)
    paint = _blend(paint, _rgb("#ffd34e"), .93 * stamen_arcs)
    paint = _blend(paint, _rgb("#080309"), .98 * negative_slits)
    paint = _blend(paint, _rgb("#8bcf55"), .78 * sepal_hooks)

    hue_null = np.full((S, S), .025, np.float32)
    for name, level in (
        ("exposed_petal_A", .34), ("exposed_petal_B", .56),
        ("collision_underfolds", .19), ("redirected_midribs", .91),
        ("secondary_veins", .69), ("curled_margins", .82),
        ("tear_lips", .13), ("dew_cups", .97), ("stamen_arcs", .88),
        ("negative_slits", .02), ("sepal_hooks", .63),
    ):
        hue_null = hue_null * (1.0 - masks[name]) + level * masks[name]
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    # Three literal, independently authored material histories.  Metallic is
    # vascular transport, roughness is exposure/underfold/tear age, and coat is
    # moisture/curl/dew deposition.  They do not share a rank map or mask write.
    vascular_phase = _f(.5 + .5 * np.sin(TAU * (5.0 * p - 3.0 * q + age)))
    metal_field = _f(
        .05 + .55 * redirected_midribs + .31 * secondary_veins
        + .27 * stamen_arcs + .19 * sepal_hooks
        + .14 * face_a * vascular_phase - .13 * negative_slits
    )
    rough_field = _f(
        .18 + .48 * face_b * (.22 + .78 * (1.0 - tissue_tone))
        + .36 * collision_underfolds + .29 * tear_lips
        + .18 * negative_slits - .31 * dew_cups - .16 * redirected_midribs
    )
    moisture = _f(.5 + .5 * np.cos(TAU * (2.7 * p + 1.9 * q - 1.3 * age)))
    coat_field = _f(
        .04 + .58 * dew_cups + .37 * curled_margins + .28 * stamen_arcs
        + .23 * face_a * moisture + .17 * secondary_veins
        - .20 * tear_lips - .16 * negative_slits
    )
    metal = np.clip(8.0 + 246.0 * metal_field, 0, 255).astype(np.float32)
    rough = np.clip(16.0 + 232.0 * rough_field, 0, 255).astype(np.float32)
    coat = np.clip(6.0 + 248.0 * coat_field, 0, 255).astype(np.float32)

    marks = tuple((name, _f(mask), banks[name]) for name, mask in masks.items())
    flat = [name for name, mask, _owner in marks if float(mask.std()) < .0015]
    if flat:
        raise ValueError(f"Pink Rose I1 has flat causal families: {flat}")
    return Grammar(marks, _f(paint), _f(hue_null), (metal, rough, coat))


@lru_cache(maxsize=1)
def i1_pink_rose() -> Grammar:
    return _compose_pink_rose(_petal_tissue, "sparse")


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fbl_pink_rose": i1_pink_rose,
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
    i1_pink_rose.cache_clear()


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
    "_compose_pink_rose",
]
