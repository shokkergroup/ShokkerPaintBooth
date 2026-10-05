# -*- coding: utf-8 -*-
"""Pink Rose PR-I6: fine-event Fibonacci meristem tissue candidate.

PR-I5 was visually strong but owner-eye review found that its hidden laminae
were authored 129--215 native pixels wide.  I6 removes every macro primitive.
Its only deposited bodies are unequal 8--32 px bent micro-laminae placed by a
deterministic low-discrepancy Fibonacci chronology.  Larger rose tissue can
exist only as the causal overlap/fusion of those fine events.  No random field,
noise image, repeated stamp, central hub, row, grid, or production hook exists.

Candidate evidence only; NOT owner accepted and deliberately unwired.
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


SQRT2M1 = np.float32(np.sqrt(2.0) - 1.0)
SILVER = np.float32(np.sqrt(2.0))


def _qphase(x, y):
    """Five-wave golden quasicrystal phase; structured, never random/noise."""
    out = np.zeros_like(np.asarray(x, np.float32))
    for j, weight in enumerate((1.0, .82, .68, .55, .43)):
        angle = np.float32(j) * GA + np.float32(.173)
        carrier = (np.cos(angle) * x + np.sin(angle) * y)
        out += np.float32(weight) * np.sin(
            TAU * np.float32(13.0 + 2.0 * j) * carrier
            + np.float32(j * j) * np.float32(.619)
        )
    return out.astype(np.float32)


def _polyline(canvas, cx, cy, theta, length, width, bend, value=1.0):
    """Deposit one open bent event whose authored extent never exceeds 32 px."""
    ct, st = float(np.cos(theta)), float(np.sin(theta))
    nx, ny = -st, ct
    half = .5 * float(length)
    points = np.asarray([
        (cx - half * ct, cy - half * st),
        (cx + float(bend) * nx, cy + float(bend) * ny),
        (cx + half * ct, cy + half * st),
    ], np.float32)
    points = np.rint(points).astype(np.int32).reshape((-1, 1, 2))
    cv2.polylines(canvas, [points], False, float(value), int(width), cv2.LINE_AA)


def _arc(canvas, cx, cy, theta, diameter, width, sweep, value=1.0):
    radius_x = max(2, int(round(.5 * diameter)))
    radius_y = max(1, int(round(.34 * diameter)))
    cv2.ellipse(
        canvas, (int(round(cx)), int(round(cy))), (radius_x, radius_y),
        float(np.degrees(theta)), float(-.5 * sweep), float(.5 * sweep),
        float(value), int(width), cv2.LINE_AA,
    )


@lru_cache(maxsize=1)
def _fine_meristem():
    body_a = np.zeros((S, S), np.float32)
    body_b = np.zeros((S, S), np.float32)
    events = []
    authored_widths_native = []
    authored_extents_native = []

    # Fibonacci count and low-discrepancy chronology give dense, non-gridded
    # coverage.  Each deposited event is an open bent stroke 2--8 source px
    # (8--32 native px); no closed petal or macro carrier is ever drawn.
    count = 6765
    for i in range(count):
        fi = np.float32(i + .5)
        u = float(np.mod(
            fi * PHI_INV + .041 * np.sin(fi * np.float32(.754877666)), 1.0
        ))
        v = float(np.mod(
            fi * SQRT2M1 + .037 * np.cos(fi * np.float32(.569840291)), 1.0
        ))
        cx, cy = u * S, v * S

        # A smooth three-mode meristem strain turns independent short events;
        # it never joins them into a long path.
        vx = (
            np.cos(TAU * (1.0 * u + PHI_INV * v))
            + .72 * np.cos(TAU * (SILVER * u - .73 * v) + .71)
            + .43 * np.sin(TAU * (.62 * u + 1.91 * v) - 1.13)
        )
        vy = (
            np.sin(TAU * (1.0 * u + PHI_INV * v))
            - .67 * np.sin(TAU * (SILVER * u - .73 * v) + .71)
            + .49 * np.cos(TAU * (.62 * u + 1.91 * v) - 1.13)
        )
        theta = float(np.arctan2(vy, vx) + .21 * np.sin(fi * GA * .071))

        extent = int(np.clip(np.rint(
            5.0 + 3.0 * (.5 + .5 * np.sin(fi * np.float32(1.324717957)))
        ), 2, 8))
        width = int(np.clip(np.rint(
            2.0 + 4.0 * (.5 + .5 * np.cos(fi * np.float32(1.220744085)))
        ), 2, 6))
        bend = float((.16 + .26 * np.sin(fi * np.float32(.438447187)))
                     * extent)

        # Owner lineage is a local five-wave Fibonacci interference state.
        # It is deterministic causal structure, not a seed/noise discriminator.
        lineage = float(_qphase(np.float32(u), np.float32(v)))
        owner_a = lineage + .34 * np.sin(2.0 * theta + fi * GA * .013) >= 0.0
        target = body_a if owner_a else body_b
        _polyline(target, cx, cy, theta, extent, width, bend)
        events.append((cx, cy, theta, extent, width, bend, fi, owner_a))
        authored_widths_native.append(width * 4)
        authored_extents_native.append(extent * 4)

    # Only an 8 px-native causal fusion radius is used.  Larger surfaces are
    # emergent overlap clusters, never authored kernels.
    support_a = cv2.GaussianBlur(body_a, (0, 0), 1.35)
    support_b = cv2.GaussianBlur(body_b, (0, 0), 1.35)
    support_a = _n(support_a)
    support_b = _n(support_b)
    total = np.maximum(support_a + support_b, 1e-5)
    balance = ((support_a - support_b) / total).astype(np.float32)
    overlap = _f(2.0 * np.minimum(support_a, support_b))

    gy_a, gx_a = np.gradient(support_a)
    gy_b, gx_b = np.gradient(support_b)
    defect = _n(np.hypot(gx_a - gx_b, gy_a - gy_b))
    collision = _f(overlap * (.28 + .72 * defect))

    lamina_a = _soft_gt(balance, .015, .24)
    lamina_b = _soft_gt(-balance, .015, .24)
    collision_underfolds = _f(
        _soft_gt(collision, .19, .075)
        * _soft_gt(np.abs(balance), .04, .12)
    )

    redirected_midribs = np.zeros((S, S), np.float32)
    secondary_veins = np.zeros((S, S), np.float32)
    curled_margins = np.zeros((S, S), np.float32)
    tear_lips = np.zeros((S, S), np.float32)
    dew_cups = np.zeros((S, S), np.float32)
    stamen_arcs = np.zeros((S, S), np.float32)
    negative_slits = np.zeros((S, S), np.float32)
    sepal_hooks = np.zeros((S, S), np.float32)

    anatomy_widths_native = {
        "redirected_midribs": [], "secondary_veins": [],
        "curled_margins": [], "tear_lips": [], "dew_cups": [],
        "stamen_arcs": [], "negative_slits": [], "sepal_hooks": [],
    }
    anatomy_extents_native = {key: [] for key in anatomy_widths_native}

    # Anatomy can appear only at causal collision/defect events.  Chronology
    # partitions the events among unlike physical families; no kit is stamped
    # into every body.  All geometry remains within the same 8--32 px budget.
    for cx, cy, theta, extent, width, bend, fi, owner_a in events:
        xi = min(S - 1, max(0, int(cx)))
        yi = min(S - 1, max(0, int(cy)))
        c = float(collision[yi, xi])
        d = float(defect[yi, xi])
        phase = float(np.mod(fi * PHI_INV + .19 * c + .11 * d, 1.0))
        if c < .12 and d < .30:
            continue

        local_extent = int(np.clip(3 + (extent + int(fi)) % 6, 3, 8))
        local_width = int(np.clip(2 + (width + int(fi)) % 3, 2, 4))
        turn = theta + float(.31 * np.sin(fi * np.float32(.271828183)))

        if phase < .052:
            _polyline(redirected_midribs, cx, cy, turn, local_extent,
                      local_width, -.34 * bend)
            name = "redirected_midribs"
        elif phase < .112:
            _polyline(secondary_veins, cx, cy, turn, local_extent,
                      local_width, .22 * bend)
            branch_extent = max(2, min(5, local_extent - 2))
            _polyline(secondary_veins, cx, cy, turn + .78, branch_extent,
                      2, -.18 * bend)
            name = "secondary_veins"
        elif phase < .161:
            _arc(curled_margins, cx, cy, turn, local_extent, local_width,
                 188.0)
            name = "curled_margins"
        elif phase < .190 and d > .42:
            _polyline(tear_lips, cx, cy, turn + 1.02, local_extent,
                      local_width, .39 * bend)
            name = "tear_lips"
        elif phase < .214 and c > .22:
            diameter = max(4, min(8, local_extent))
            cv2.circle(dew_cups, (int(round(cx)), int(round(cy))),
                       max(2, diameter // 2), 1.0, local_width, cv2.LINE_AA)
            local_extent = diameter
            name = "dew_cups"
        elif phase < .247:
            _arc(stamen_arcs, cx, cy, turn, local_extent, local_width, 136.0)
            name = "stamen_arcs"
        elif phase < .284 and d > .36:
            _polyline(negative_slits, cx, cy, turn - .61, local_extent,
                      local_width, 0.0)
            name = "negative_slits"
        elif phase < .316 and not owner_a:
            _polyline(sepal_hooks, cx, cy, turn + .92, local_extent,
                      local_width, .52 * local_extent)
            name = "sepal_hooks"
        else:
            continue

        anatomy_widths_native[name].append(local_width * 4)
        anatomy_extents_native[name].append(local_extent * 4)

    masks = {
        "micro_lamina_A": _f(lamina_a),
        "micro_lamina_B": _f(lamina_b),
        "collision_underfolds": _f(collision_underfolds),
        "redirected_midribs": _f(redirected_midribs),
        "secondary_veins": _f(secondary_veins),
        "curled_margins": _f(curled_margins),
        "tear_lips": _f(tear_lips),
        "dew_cups": _f(dew_cups),
        "stamen_arcs": _f(stamen_arcs),
        "negative_slits": _f(negative_slits),
        "sepal_hooks": _f(sepal_hooks),
    }

    meta = {
        "primary_widths_native": tuple(authored_widths_native),
        "primary_extents_native": tuple(authored_extents_native),
        "anatomy_widths_native": {
            key: tuple(values) for key, values in anatomy_widths_native.items()
        },
        "anatomy_extents_native": {
            key: tuple(values) for key, values in anatomy_extents_native.items()
        },
        "event_count": count,
        "fusion_sigma_native": 5.4,
    }
    return masks, balance, overlap, collision, defect, meta


@lru_cache(maxsize=1)
def i6_pink_rose() -> Grammar:
    masks, balance, overlap, collision, defect, _meta = _fine_meristem()
    lamina_a, lamina_b = masks["micro_lamina_A"], masks["micro_lamina_B"]

    rose_bank = [_rgb(c) for c in (
        "#210712", "#3d0b1c", "#5b1028", "#7b1835", "#9c2544",
        "#bc3655", "#d74c68", "#ec6980", "#f68a9c", "#fbb0ba",
        "#ffd0d4", "#ffe9e8",
    )]
    violet_bank = [_rgb(c) for c in (
        "#10071e", "#21102f", "#361744", "#4d205a", "#652b71",
        "#7d3989", "#974aa1", "#b05eb8", "#c778ce", "#db98df",
        "#eab9eb", "#f8dbf5",
    )]
    orientation_tone = _n(_qphase(U + .07 * balance, V - .05 * balance))
    tone_a = _f(.36 * _n(overlap) + .34 * orientation_tone
                + .30 * _n(defect))
    tone_b = _f(.40 * (1.0 - orientation_tone) + .32 * _n(collision)
                + .28 * _n(np.abs(balance)))
    color_a = _palette(tone_a, rose_bank)
    color_b = _palette(tone_b, violet_bank)
    total = np.maximum(lamina_a + lamina_b, 1e-5)
    paint = (color_a * (lamina_a / total)[..., None]
             + color_b * (lamina_b / total)[..., None])
    paint = _blend(paint, _rgb("#4a102f"), .68 * masks["collision_underfolds"])
    paint = _blend(paint, _rgb("#ffd9de"), .92 * masks["redirected_midribs"])
    paint = _blend(paint, _rgb("#ff6f91"), .86 * masks["secondary_veins"])
    paint = _blend(paint, _rgb("#ffb7cb"), .88 * masks["curled_margins"])
    paint = _blend(paint, _rgb("#651027"), .96 * masks["tear_lips"])
    paint = _blend(paint, _rgb("#bcefff"), .98 * masks["dew_cups"])
    paint = _blend(paint, _rgb("#ffd447"), .98 * masks["stamen_arcs"])
    paint = _blend(paint, _rgb("#070208"), .995 * masks["negative_slits"])
    paint = _blend(paint, _rgb("#88c85a"), .91 * masks["sepal_hooks"])

    hue_null = .29 * lamina_a + .58 * lamina_b
    for name, level in (
        ("collision_underfolds", .13), ("redirected_midribs", .94),
        ("secondary_veins", .72), ("curled_margins", .84),
        ("tear_lips", .09), ("dew_cups", .99), ("stamen_arcs", .89),
        ("negative_slits", .015), ("sepal_hooks", .64),
    ):
        hue_null = hue_null * (1.0 - masks[name]) + level * masks[name]
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    # Literal, separately authored channel mechanics.  None is a recolor or
    # shared threshold substrate: M follows vascular exposure, R collision age,
    # and Cc cup/curl wetness with different causal interactions.
    vascular = _n(
        masks["redirected_midribs"] + .72 * masks["secondary_veins"]
        + .48 * masks["stamen_arcs"] + .24 * lamina_a * (1.0 - overlap)
    )
    fracture = _n(
        masks["collision_underfolds"] + .82 * masks["tear_lips"]
        + .52 * masks["negative_slits"] + .31 * lamina_b * defect
    )
    wetness = _n(
        masks["dew_cups"] + .76 * masks["curled_margins"]
        + .44 * masks["stamen_arcs"] + .22 * lamina_a * overlap
        - .31 * masks["tear_lips"]
    )
    metal = np.clip(6.0 + 248.0 * _f(.05 + .88 * vascular), 0, 255)
    rough = np.clip(13.0 + 235.0 * _f(.10 + .80 * fracture), 0, 255)
    coat = np.clip(4.0 + 250.0 * _f(.04 + .91 * wetness), 0, 255)

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
        raise ValueError(f"Pink Rose I6 has flat causal families: {flat}")
    return Grammar(
        marks, _f(paint), _f(hue_null),
        (metal.astype(np.float32), rough.astype(np.float32), coat.astype(np.float32)),
    )


BUILDERS: Mapping[str, Callable[[], Grammar]] = {"fbl_pink_rose": i6_pink_rose}
HUES = {"fbl_pink_rose": (.97, .82)}
BLOOM_IDS = tuple(BUILDERS)


@lru_cache(maxsize=4)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    spec = np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)
    return grammar.paint, spec


def clear_cache():
    _authored.cache_clear()
    i6_pink_rose.cache_clear()
    _fine_meristem.cache_clear()


def debug_grammar(fid: str):
    return BUILDERS[fid]()


def debug_hue_null(fid: str):
    return debug_grammar(fid).hue_null


def debug_primary_measurements(fid: str = "fbl_pink_rose"):
    if fid not in BUILDERS:
        raise KeyError(fid)
    return _fine_meristem()[-1]


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
