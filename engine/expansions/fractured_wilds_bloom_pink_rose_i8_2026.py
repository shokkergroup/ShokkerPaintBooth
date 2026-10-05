# -*- coding: utf-8 -*-
"""Pink Rose PR-I8: clustered fine-lamina territory collision.

I6 was a fine-width labyrinth and I7 became unstructured confetti.  I8 uses
144 unequal, edge-cropped Fibonacci territories, but a territory is never a
drawn shape: it exists only as a cluster of open 8--32 px micro-lamina events.
Clusters overlap additively and have no rendered outline or winner surface.
Collision chronology redirects a sparse subset into unlike underfold, vein,
curl, tear, dew, stamen, slit, and sepal events.  Deterministic only; no random
or noise input, central hub, rows/grid, paver, repeated stamp, or long carrier.

Isolated candidate only; NOT owner accepted and deliberately unwired.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import cv2
import numpy as np

from .fractured_wilds_bloom_pink_rose_i4_2026 import (
    S, TAU, GA, PHI_INV, U, V, Grammar, _blend, _f, _n, _palette, _rgb,
)
from .fractured_wilds_bloom_pink_rose_i6_2026 import (
    SQRT2M1, _arc, _polyline,
)


@lru_cache(maxsize=2)
def _clustered_tissue(profile="isolates"):
    body_a = np.zeros((S, S), np.float32)
    body_b = np.zeros((S, S), np.float32)
    ridge = np.zeros((S, S), np.float32)
    shade_bodies = [np.zeros((S, S), np.float32) for _ in range(8)]
    events = []
    primary_widths_native = []
    primary_extents_native = []

    fused_profile = profile == "fused"
    territory_count = 377 if fused_profile else 144
    for j in range(territory_count):
        tj = np.float32(j + .5)
        edge_origin = -.07 if fused_profile else -.10
        edge_span = 1.14 if fused_profile else 1.20
        cu = float(edge_origin + edge_span * np.mod(
            tj * PHI_INV + .023 * np.sin(tj * np.float32(.754877666)), 1.0
        ))
        cv = float(edge_origin + edge_span * np.mod(
            tj * SQRT2M1 + .019 * np.cos(tj * np.float32(.569840291)), 1.0
        ))
        cx0, cy0 = cu * S, cv * S
        theta0 = float(tj * GA + .37 * np.sin(tj * np.float32(.438447187)))
        territory_length = float(
            (16.0 if fused_profile else 20.0)
            + (18.0 if fused_profile else 24.0)
            * (.5 + .5 * np.sin(tj * np.float32(1.324717957)))
        )
        territory_half_width = float(
            (8.0 if fused_profile else 9.0)
            + (11.0 if fused_profile else 15.0)
            * (.5 + .5 * np.cos(tj * np.float32(1.220744085)))
        )
        curvature = float(.10 + .22 * np.sin(tj * np.float32(.918273645)))
        event_count = int(
            (34 if fused_profile else 55)
            + (21 if fused_profile else 34)
            * (.5 + .5 * np.sin(tj * np.float32(.682327804)))
        )
        owner_a = bool(
            np.sin(tj * np.float32(1.465571232)
                   + .31 * np.cos(tj * PHI_INV)) >= 0.0
        )
        shade = int(np.floor(np.mod(tj * PHI_INV + .13 * owner_a, 1.0) * 8.0))
        ct0, st0 = float(np.cos(theta0)), float(np.sin(theta0))
        nx0, ny0 = -st0, ct0

        for k in range(event_count):
            fk = np.float32(k + .5)
            along_phase = float(2.0 * np.mod(fk * PHI_INV, 1.0) - 1.0)
            across_phase = float(2.0 * np.mod(fk * SQRT2M1, 1.0) - 1.0)
            taper = float(np.power(max(0.0, 1.0 - abs(along_phase)), .43))
            along = territory_length * (.47 * along_phase
                                         + .065 * along_phase * along_phase)
            across = territory_half_width * taper * across_phase
            across += curvature * territory_half_width * (
                along_phase * along_phase - .33
            )
            cx = cx0 + along * ct0 + across * nx0
            cy = cy0 + along * st0 + across * ny0
            theta = float(
                theta0 + .28 * across_phase + .19 * along_phase
                + .13 * np.sin(fk * GA + tj * .31)
            )
            extent = int(np.clip(np.rint(
                3.0 + 5.0 * (.5 + .5 * np.sin(
                    fk * np.float32(1.324717957) + tj * .17
                ))
            ), 2, 8))
            width = int(np.clip(np.rint(
                2.0 + 4.0 * (.5 + .5 * np.cos(
                    fk * np.float32(1.220744085) - tj * .11
                ))
            ), 2, 6))
            bend = float(
                (.10 + .29 * np.sin(fk * np.float32(.438447187) + tj * .07))
                * extent
            )
            target = body_a if owner_a else body_b
            _polyline(target, cx, cy, theta, extent, width, bend)
            _polyline(shade_bodies[shade], cx, cy, theta, extent, width, bend)
            if float(np.sin(fk * .73 + tj * .41)) > .24:
                _polyline(ridge, cx, cy, theta + .08, extent,
                          max(2, width - 2), -.38 * bend)
            events.append((cx, cy, theta, extent, width, bend, tj, fk,
                           owner_a, shade))
            primary_widths_native.append(width * 4)
            primary_extents_native.append(extent * 4)

    support_a = _n(cv2.GaussianBlur(body_a, (0, 0), 1.15))
    support_b = _n(cv2.GaussianBlur(body_b, (0, 0), 1.15))
    support_all = _n(cv2.GaussianBlur(np.maximum(body_a, body_b), (0, 0), 1.05))
    ridge = _n(cv2.GaussianBlur(ridge, (0, 0), .55))
    shade_support = [cv2.GaussianBlur(value, (0, 0), 1.05)
                     for value in shade_bodies]
    shade_sum = np.maximum(np.sum(shade_support, axis=0), 1e-5)
    shade_tone = np.zeros((S, S), np.float32)
    for i, support in enumerate(shade_support):
        shade_tone += np.float32(i / 7.0) * support
    shade_tone = _f(shade_tone / shade_sum)

    total = np.maximum(support_a + support_b, 1e-5)
    owner_mix = _f(.06 + .88 * support_a / total)
    overlap = _f(2.0 * np.minimum(support_a, support_b))
    gy_a, gx_a = np.gradient(support_a)
    gy_b, gx_b = np.gradient(support_b)
    defect = _n(np.hypot(gx_a - gx_b, gy_a - gy_b)
                + .31 * np.hypot(*np.gradient(shade_tone)))

    anatomy = {
        name: np.zeros((S, S), np.float32) for name in (
            "collision_underfolds", "redirected_midribs", "secondary_veins",
            "curled_margins", "tear_lips", "dew_cups", "stamen_arcs",
            "negative_slits", "sepal_hooks",
        )
    }
    widths = {name: [] for name in anatomy}
    extents = {name: [] for name in anatomy}

    for cx, cy, theta, extent, width, bend, tj, fk, owner_a, shade in events:
        xi = min(S - 1, max(0, int(cx)))
        yi = min(S - 1, max(0, int(cy)))
        ov = float(overlap[yi, xi])
        df = float(defect[yi, xi])
        phase = float(np.mod(
            fk * np.float32(.754877666) + tj * np.float32(.131652498)
            + .061 * ov + .037 * shade, 1.0
        ))
        if ov < .055 and support_all[yi, xi] < .22:
            continue
        local_extent = int(np.clip(3 + (extent + int(fk + tj)) % 6, 3, 8))
        local_width = int(np.clip(2 + (width + int(fk)) % 3, 2, 4))
        turn = theta + float(.31 * np.sin(fk * .29 + tj * .17))

        if phase < .012:
            _arc(anatomy["collision_underfolds"], cx, cy, turn,
                 local_extent, local_width, 178.0)
            name = "collision_underfolds"
        elif phase < .022:
            _polyline(anatomy["redirected_midribs"], cx, cy, turn,
                      local_extent, local_width, -.35 * bend)
            name = "redirected_midribs"
        elif phase < .034:
            _polyline(anatomy["secondary_veins"], cx, cy, turn,
                      local_extent, local_width, .21 * bend)
            _polyline(anatomy["secondary_veins"], cx, cy, turn + .75,
                      max(2, local_extent - 3), 2, -.15 * bend)
            name = "secondary_veins"
        elif phase < .044:
            _arc(anatomy["curled_margins"], cx, cy, turn,
                 local_extent, local_width, 199.0)
            name = "curled_margins"
        elif phase < .053 and df > .18:
            _polyline(anatomy["tear_lips"], cx, cy, turn + .96,
                      local_extent, local_width, .40 * bend)
            name = "tear_lips"
        elif phase < .060 and ov > .08:
            diameter = max(4, min(8, local_extent))
            cv2.circle(anatomy["dew_cups"], (int(round(cx)), int(round(cy))),
                       max(2, diameter // 2), 1.0, local_width, cv2.LINE_AA)
            local_extent = diameter
            name = "dew_cups"
        elif phase < .068:
            _arc(anatomy["stamen_arcs"], cx, cy, turn,
                 local_extent, local_width, 133.0)
            name = "stamen_arcs"
        elif phase < .075 and df > .17:
            _polyline(anatomy["negative_slits"], cx, cy, turn - .63,
                      local_extent, local_width, 0.0)
            name = "negative_slits"
        elif phase < .083 and not owner_a:
            _polyline(anatomy["sepal_hooks"], cx, cy, turn + .90,
                      local_extent, local_width, .48 * local_extent)
            name = "sepal_hooks"
        else:
            continue
        widths[name].append(local_width * 4)
        extents[name].append(local_extent * 4)

    masks = {
        "micro_lamina_A": _f(.10 + .90 * support_a),
        "micro_lamina_B": _f(.10 + .90 * support_b),
        **{key: _f(value) for key, value in anatomy.items()},
    }
    meta = {
        "territory_count": territory_count,
        "event_count": len(events),
        "primary_widths_native": tuple(primary_widths_native),
        "primary_extents_native": tuple(primary_extents_native),
        "anatomy_widths_native": {key: tuple(value) for key, value in widths.items()},
        "anatomy_extents_native": {key: tuple(value) for key, value in extents.items()},
        "profile": profile,
        "fusion_sigma_native": 4.6,
    }
    return (masks, support_a, support_b, support_all, ridge, shade_tone,
            owner_mix, overlap, defect, meta)


@lru_cache(maxsize=1)
def i8_pink_rose() -> Grammar:
    (masks, support_a, support_b, support_all, ridge, shade_tone,
     owner_mix, overlap, defect, _meta) = _clustered_tissue()
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
    tone_a = _f(.19 + .55 * shade_tone + .17 * ridge + .09 * overlap)
    tone_b = _f(.17 + .52 * (1.0 - shade_tone) + .19 * defect
                + .12 * support_all)
    color_a = _palette(tone_a, rose_bank)
    color_b = _palette(tone_b, violet_bank)
    paint = color_a * owner_mix[..., None] + color_b * (1.0 - owner_mix)[..., None]
    paint = _blend(paint, _rgb("#ff9db0"), .26 * ridge * support_a)
    paint = _blend(paint, _rgb("#67204f"), .21 * ridge * support_b)
    paint = _blend(paint, _rgb("#4b102f"), .72 * masks["collision_underfolds"])
    paint = _blend(paint, _rgb("#ffd9df"), .90 * masks["redirected_midribs"])
    paint = _blend(paint, _rgb("#ff7593"), .82 * masks["secondary_veins"])
    paint = _blend(paint, _rgb("#ffb7cb"), .85 * masks["curled_margins"])
    paint = _blend(paint, _rgb("#651027"), .94 * masks["tear_lips"])
    paint = _blend(paint, _rgb("#bcefff"), .96 * masks["dew_cups"])
    paint = _blend(paint, _rgb("#ffd447"), .96 * masks["stamen_arcs"])
    paint = _blend(paint, _rgb("#070208"), .995 * masks["negative_slits"])
    paint = _blend(paint, _rgb("#88c85a"), .88 * masks["sepal_hooks"])

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
        + .46 * masks["stamen_arcs"] + .26 * ridge * support_a
    )
    fracture = _n(
        masks["collision_underfolds"] + .80 * masks["tear_lips"]
        + .50 * masks["negative_slits"] + .29 * defect * support_b
    )
    wetness = _n(
        masks["dew_cups"] + .74 * masks["curled_margins"]
        + .42 * masks["stamen_arcs"] + .25 * overlap * support_a
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
        raise ValueError(f"Pink Rose I8 has flat causal families: {flat}")
    return Grammar(
        marks, _f(paint), _f(hue_null),
        (metal.astype(np.float32), rough.astype(np.float32), coat.astype(np.float32)),
    )


BUILDERS: Mapping[str, Callable[[], Grammar]] = {"fbl_pink_rose": i8_pink_rose}
HUES = {"fbl_pink_rose": (.97, .82)}
BLOOM_IDS = tuple(BUILDERS)


@lru_cache(maxsize=4)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    spec = np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)
    return grammar.paint, spec


def clear_cache():
    _authored.cache_clear()
    i8_pink_rose.cache_clear()
    _clustered_tissue.cache_clear()


def debug_grammar(fid: str):
    return BUILDERS[fid]()


def debug_hue_null(fid: str):
    return debug_grammar(fid).hue_null


def debug_primary_measurements(fid: str = "fbl_pink_rose"):
    if fid not in BUILDERS:
        raise KeyError(fid)
    return _clustered_tissue()[-1]


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
