# -*- coding: utf-8 -*-
"""Pink Rose PR-I7: fused fine-lamina chronology repair.

I6 proved the 8--32 px primitive budget but exposed its ownership interference
as a generic labyrinth with anatomy bands.  I7 keeps only the valid physical
premise: 10,946 deterministic Fibonacci micro-lamina events, each 8--32 px.
Their overlaps create one seamless rose tissue.  A/B lineage is a smooth
multi-axis meristem state, while collision anatomy is deposited as short,
unequal local events instead of painted boundaries.  No random/noise source,
macro primitive, stamp census, hub, grid, row, or long carrier is present.

Isolated candidate only; NOT owner accepted and deliberately unwired.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import cv2
import numpy as np

from .fractured_wilds_bloom_pink_rose_i4_2026 import (
    S, TAU, GA, PHI_INV, U, V, Grammar, _blend, _f, _n, _palette, _rgb,
    _soft_gt,
)
from .fractured_wilds_bloom_pink_rose_i6_2026 import (
    SQRT2M1, SILVER, _arc, _polyline,
)


def _meristem_state(u, v):
    """Smooth non-banded lineage made from three oblique causal strains."""
    u = np.asarray(u, np.float32)
    v = np.asarray(v, np.float32)
    return (
        1.00 * np.sin(TAU * (1.13 * u + .71 * v)
                      + .58 * np.sin(TAU * (.43 * u - .89 * v)))
        + .73 * np.cos(TAU * (-.67 * u + 1.37 * v)
                       + .41 * np.sin(TAU * (1.21 * u + .26 * v)))
        + .46 * np.sin(TAU * (1.79 * u - .83 * v)
                       + .29 * np.cos(TAU * (.31 * u + 1.11 * v)))
    ).astype(np.float32)


def _event_geometry(fi, u, v):
    # This smooth strain guides independent short pieces only; no event is
    # connected to its predecessor and no long streamline is ever authored.
    vx = (
        np.cos(TAU * (.91 * u + PHI_INV * v))
        + .69 * np.cos(TAU * (SILVER * u - .61 * v) + .83)
        + .39 * np.sin(TAU * (.47 * u + 1.73 * v) - 1.07)
    )
    vy = (
        np.sin(TAU * (.91 * u + PHI_INV * v))
        - .63 * np.sin(TAU * (SILVER * u - .61 * v) + .83)
        + .45 * np.cos(TAU * (.47 * u + 1.73 * v) - 1.07)
    )
    theta = float(np.arctan2(vy, vx) + .17 * np.sin(fi * GA * .037))
    extent = int(np.clip(np.rint(
        3.0 + 5.0 * (.5 + .5 * np.sin(fi * np.float32(1.324717957)))
    ), 2, 8))
    width = int(np.clip(np.rint(
        2.0 + 4.0 * (.5 + .5 * np.cos(fi * np.float32(1.220744085)))
    ), 2, 6))
    bend = float((.12 + .30 * np.sin(fi * np.float32(.438447187))) * extent)
    return theta, extent, width, bend


@lru_cache(maxsize=1)
def _fused_fine_tissue():
    body_all = np.zeros((S, S), np.float32)
    micro_ridge = np.zeros((S, S), np.float32)
    events = []
    primary_widths_native = []
    primary_extents_native = []

    count = 10946  # Fibonacci number; dense enough for seamless fused tissue.
    for i in range(count):
        fi = np.float32(i + .5)
        u = float(np.mod(
            fi * PHI_INV + .029 * np.sin(fi * np.float32(.754877666)), 1.0
        ))
        v = float(np.mod(
            fi * SQRT2M1 + .027 * np.cos(fi * np.float32(.569840291)), 1.0
        ))
        cx, cy = u * S, v * S
        theta, extent, width, bend = _event_geometry(fi, u, v)
        _polyline(body_all, cx, cy, theta, extent, width, bend)
        # A narrower causal ridge inside only some lamina events preserves a
        # visible picker-scale microfold without turning all pieces into stamps.
        if float(np.sin(fi * np.float32(.918273645))) > .18:
            _polyline(micro_ridge, cx, cy, theta + .09, extent,
                      max(2, width - 2), -.42 * bend)
        events.append((cx, cy, theta, extent, width, bend, fi, u, v))
        primary_widths_native.append(width * 4)
        primary_extents_native.append(extent * 4)

    # Five native pixels of fusion is less than one minimum authored mark.
    # Broad color regions below are lineage mixtures, not shape primitives.
    support = _n(cv2.GaussianBlur(body_all, (0, 0), 1.22))
    ridge = _n(cv2.GaussianBlur(micro_ridge, (0, 0), .58))
    lineage = _meristem_state(U, V)
    owner_mix = _f(.5 + .46 * np.tanh(.88 * lineage))
    micro_lamina_a = _f(.16 + .84 * support * owner_mix)
    micro_lamina_b = _f(.16 + .84 * support * (1.0 - owner_mix))

    gy_s, gx_s = np.gradient(support)
    gy_l, gx_l = np.gradient(lineage)
    defect = _n(np.hypot(gx_s, gy_s) + .29 * np.hypot(gx_l, gy_l))
    overlap = _f(4.0 * owner_mix * (1.0 - owner_mix) * support)

    anatomy = {
        name: np.zeros((S, S), np.float32) for name in (
            "collision_underfolds", "redirected_midribs", "secondary_veins",
            "curled_margins", "tear_lips", "dew_cups", "stamen_arcs",
            "negative_slits", "sepal_hooks",
        )
    }
    widths = {name: [] for name in anatomy}
    extents = {name: [] for name in anatomy}

    # The anatomy selector is chronology plus local overlap/lineage state.
    # Its narrow disjoint intervals yield unlike, distributed families rather
    # than the I6 vertical collision corridors.
    for cx, cy, theta, extent, width, bend, fi, u, v in events:
        xi = min(S - 1, max(0, int(cx)))
        yi = min(S - 1, max(0, int(cy)))
        ov = float(overlap[yi, xi])
        df = float(defect[yi, xi])
        ln = float(lineage[yi, xi])
        phase = float(np.mod(
            fi * np.float32(.754877666) + .071 * ov + .047 * ln, 1.0
        ))
        if ov < .08:
            continue
        local_extent = int(np.clip(3 + (extent + int(fi)) % 6, 3, 8))
        local_width = int(np.clip(2 + (width + int(fi)) % 3, 2, 4))
        turn = theta + float(.33 * np.sin(fi * np.float32(.271828183)))

        if phase < .026:
            _arc(anatomy["collision_underfolds"], cx, cy, turn,
                 local_extent, local_width, 176.0)
            name = "collision_underfolds"
        elif phase < .047:
            _polyline(anatomy["redirected_midribs"], cx, cy, turn,
                      local_extent, local_width, -.36 * bend)
            name = "redirected_midribs"
        elif phase < .070:
            _polyline(anatomy["secondary_veins"], cx, cy, turn,
                      local_extent, local_width, .22 * bend)
            _polyline(anatomy["secondary_veins"], cx, cy, turn + .72,
                      max(2, local_extent - 3), 2, -.16 * bend)
            name = "secondary_veins"
        elif phase < .088:
            _arc(anatomy["curled_margins"], cx, cy, turn,
                 local_extent, local_width, 202.0)
            name = "curled_margins"
        elif phase < .100 and df > .31:
            _polyline(anatomy["tear_lips"], cx, cy, turn + .97,
                      local_extent, local_width, .41 * bend)
            name = "tear_lips"
        elif phase < .111:
            diameter = max(4, min(8, local_extent))
            cv2.circle(anatomy["dew_cups"], (int(round(cx)), int(round(cy))),
                       max(2, diameter // 2), 1.0, local_width, cv2.LINE_AA)
            local_extent = diameter
            name = "dew_cups"
        elif phase < .123:
            _arc(anatomy["stamen_arcs"], cx, cy, turn,
                 local_extent, local_width, 131.0)
            name = "stamen_arcs"
        elif phase < .134 and df > .27:
            _polyline(anatomy["negative_slits"], cx, cy, turn - .64,
                      local_extent, local_width, 0.0)
            name = "negative_slits"
        elif phase < .145 and ln < -.12:
            _polyline(anatomy["sepal_hooks"], cx, cy, turn + .88,
                      local_extent, local_width, .49 * local_extent)
            name = "sepal_hooks"
        else:
            continue
        widths[name].append(local_width * 4)
        extents[name].append(local_extent * 4)

    masks = {
        "micro_lamina_A": micro_lamina_a,
        "micro_lamina_B": micro_lamina_b,
        **{key: _f(value) for key, value in anatomy.items()},
    }
    meta = {
        "event_count": count,
        "primary_widths_native": tuple(primary_widths_native),
        "primary_extents_native": tuple(primary_extents_native),
        "anatomy_widths_native": {key: tuple(value) for key, value in widths.items()},
        "anatomy_extents_native": {key: tuple(value) for key, value in extents.items()},
        "fusion_sigma_native": 4.88,
    }
    return masks, support, ridge, lineage, owner_mix, overlap, defect, meta


@lru_cache(maxsize=1)
def i7_pink_rose() -> Grammar:
    masks, support, ridge, lineage, owner_mix, overlap, defect, _meta = (
        _fused_fine_tissue()
    )
    lamina_a, lamina_b = masks["micro_lamina_A"], masks["micro_lamina_B"]

    rose_bank = [_rgb(c) for c in (
        "#260812", "#400c1c", "#5d1228", "#7c1a36", "#9d2746",
        "#bd3857", "#d84e6a", "#ec6b82", "#f58b9d", "#fbb0bb",
        "#ffd0d5", "#ffe9e9",
    )]
    violet_bank = [_rgb(c) for c in (
        "#11071e", "#21102f", "#351744", "#4b2059", "#622b70",
        "#793887", "#93499f", "#ac5db6", "#c477cc", "#da97de",
        "#eab9eb", "#f8dbf5",
    )]
    # Color tone is material chronology/support, not another rendered carrier.
    chronology = _n(
        .46 * support + .28 * ridge + .17 * defect
        + .09 * np.cos(TAU * (.71 * U + 1.13 * V) + .21 * lineage)
    )
    color_a = _palette(chronology, rose_bank)
    color_b = _palette(_f(.18 + .72 * (1.0 - chronology) + .10 * overlap),
                       violet_bank)
    paint = color_a * owner_mix[..., None] + color_b * (1.0 - owner_mix)[..., None]
    # Fine body relief is visible without drawing closed ownership boundaries.
    paint = _blend(paint, _rgb("#ff9eb0"), .17 * ridge * owner_mix)
    paint = _blend(paint, _rgb("#6d1b50"), .14 * ridge * (1.0 - owner_mix))
    paint = _blend(paint, _rgb("#4b102f"), .73 * masks["collision_underfolds"])
    paint = _blend(paint, _rgb("#ffd9df"), .91 * masks["redirected_midribs"])
    paint = _blend(paint, _rgb("#ff7593"), .83 * masks["secondary_veins"])
    paint = _blend(paint, _rgb("#ffb7cb"), .86 * masks["curled_margins"])
    paint = _blend(paint, _rgb("#651027"), .95 * masks["tear_lips"])
    paint = _blend(paint, _rgb("#bcefff"), .97 * masks["dew_cups"])
    paint = _blend(paint, _rgb("#ffd447"), .97 * masks["stamen_arcs"])
    paint = _blend(paint, _rgb("#070208"), .995 * masks["negative_slits"])
    paint = _blend(paint, _rgb("#88c85a"), .89 * masks["sepal_hooks"])

    hue_null = _f(.31 * owner_mix + .58 * (1.0 - owner_mix)
                  + .09 * chronology)
    for name, level in (
        ("collision_underfolds", .13), ("redirected_midribs", .94),
        ("secondary_veins", .72), ("curled_margins", .84),
        ("tear_lips", .09), ("dew_cups", .99), ("stamen_arcs", .89),
        ("negative_slits", .015), ("sepal_hooks", .64),
    ):
        hue_null = hue_null * (1.0 - masks[name]) + level * masks[name]
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    vascular = _n(
        masks["redirected_midribs"] + .71 * masks["secondary_veins"]
        + .47 * masks["stamen_arcs"] + .24 * ridge * owner_mix
    )
    fracture = _n(
        masks["collision_underfolds"] + .81 * masks["tear_lips"]
        + .51 * masks["negative_slits"] + .27 * defect * (1.0 - owner_mix)
    )
    wetness = _n(
        masks["dew_cups"] + .75 * masks["curled_margins"]
        + .43 * masks["stamen_arcs"] + .23 * overlap * owner_mix
        - .30 * masks["tear_lips"]
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
        raise ValueError(f"Pink Rose I7 has flat causal families: {flat}")
    return Grammar(
        marks, _f(paint), _f(hue_null),
        (metal.astype(np.float32), rough.astype(np.float32), coat.astype(np.float32)),
    )


BUILDERS: Mapping[str, Callable[[], Grammar]] = {"fbl_pink_rose": i7_pink_rose}
HUES = {"fbl_pink_rose": (.97, .82)}
BLOOM_IDS = tuple(BUILDERS)


@lru_cache(maxsize=4)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    spec = np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)
    return grammar.paint, spec


def clear_cache():
    _authored.cache_clear()
    i7_pink_rose.cache_clear()
    _fused_fine_tissue.cache_clear()


def debug_grammar(fid: str):
    return BUILDERS[fid]()


def debug_hue_null(fid: str):
    return debug_grammar(fid).hue_null


def debug_primary_measurements(fid: str = "fbl_pink_rose"):
    if fid not in BUILDERS:
        raise KeyError(fid)
    return _fused_fine_tissue()[-1]


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
