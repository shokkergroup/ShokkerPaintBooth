# -*- coding: utf-8 -*-
"""Isolated native-2048 Spectrolite Vein continuum study.

One hand-authored, globally connected mineral event replaces every prior
stamped/paver approach.  A single finite seam advances across the stone, sheds
ordered branches, changes cleavage at joints, develops local twin offsets,
terminates fronts, and precipitates attached exsolution needles.  There is no
cell field, lattice, grid, row, stamp, glyph library, RNG, noise, grain, FBM, or
palette-variant ancestry.

SPB-WILDS-FULLRES tick FR-S1, 2026-08-24.  Owner verdict addressed:
"2048x2048 canvas size images ... make REAL PROGRESS" and the cardinal anti-
lazy rule.  Native review verdict: REJECT.  The result reads as a generic sparse
branch diagram with repeated ladder/tick decoration, exactly matching the
reservation veto.  This module is frozen, fail-closed, isolated and unwired and
claims neither owner acceptance nor M7/release status.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, Mapping, Sequence, Tuple

import cv2
import numpy as np


ID = "fmo_spectrolite_vein"
WORK = 1024
CALM_SPEC = np.asarray((5.0, 184.0, 8.0), np.float32)


@dataclass(frozen=True)
class Branch:
    name: str
    order: int
    points: Tuple[Tuple[float, float], ...]
    twin_segments: Tuple[int, ...] = ()
    flash_joints: Tuple[int, ...] = ()
    needle_segments: Tuple[int, ...] = ()


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    hue_null: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]
    mechanism: str
    branch_names: Tuple[str, ...]
    primitive_native_px: Tuple[int, int] = (8, 32)


# Every branch begins on the trunk or an earlier branch.  Coordinates are
# deliberately finite and hand-authored: no recursive branch grammar can stamp
# the same silhouette at different positions.
BRANCHES: Tuple[Branch, ...] = (
    Branch("master_shear", 0, (
        (-42, 655), (54, 630), (103, 558), (182, 579), (237, 512),
        (315, 526), (370, 448), (442, 462), (493, 377), (566, 398),
        (622, 316), (700, 337), (751, 249), (833, 276), (885, 205),
        (1064, 171)), (1, 4, 7, 10, 13), (2, 5, 8, 11, 14),
        (0, 3, 6, 9, 12, 14)),
    Branch("northwest_release", 1, (
        (103, 558), (55, 472), (87, 390), (26, 306), (-38, 287)),
        (0, 2), (1, 3), (0, 1, 2)),
    Branch("southwest_drop", 1, (
        (182, 579), (145, 690), (206, 744), (167, 839), (221, 930),
        (196, 1060)), (1, 3), (1, 3), (0, 2, 4)),
    Branch("lower_prism_run", 1, (
        (315, 526), (337, 631), (412, 679), (438, 773), (517, 813),
        (545, 941), (621, 1060)), (0, 2, 4), (1, 3, 5), (1, 3, 4)),
    Branch("upper_cleavage_rise", 1, (
        (370, 448), (334, 359), (385, 304), (350, 219), (411, 164),
        (397, 57), (445, -32)), (1, 3, 5), (1, 3, 4), (0, 2, 4)),
    Branch("southeast_schiller_run", 1, (
        (493, 377), (517, 484), (593, 525), (612, 618), (690, 660),
        (706, 754), (788, 804), (813, 910), (887, 1035)),
        (0, 2, 5, 7), (1, 3, 6), (0, 2, 4, 6)),
    Branch("north_prism_rise", 1, (
        (622, 316), (635, 218), (704, 176), (724, 81), (802, 42),
        (830, -30)), (0, 2, 4), (1, 3), (0, 2, 3)),
    Branch("east_fan_release", 1, (
        (751, 249), (786, 362), (856, 404), (880, 496), (954, 534),
        (1038, 630)), (1, 3), (1, 3), (0, 2, 4)),
    Branch("east_crown_slip", 1, (
        (833, 276), (896, 328), (976, 311), (1056, 368)),
        (0, 2), (1,), (0, 2)),
    Branch("northwest_twin_splay", 2, (
        (87, 390), (170, 358), (202, 282), (277, 260)),
        (0, 2), (1, 2), (0, 1)),
    Branch("west_terminal_splay", 2, (
        (167, 839), (78, 810), (42, 729), (-30, 700)),
        (0,), (1,), (0, 2)),
    Branch("lower_left_exsolution", 2, (
        (438, 773), (354, 823), (328, 912), (260, 970)),
        (1,), (1, 2), (0, 2)),
    Branch("upper_left_cleavage", 2, (
        (350, 219), (262, 196), (215, 119), (113, 92)),
        (0, 2), (1,), (0, 1)),
    Branch("east_twin_shelf", 2, (
        (690, 660), (779, 623), (835, 677), (924, 650), (1005, 696)),
        (0, 2), (1, 3), (0, 2, 3)),
    Branch("north_capillary", 2, (
        (704, 176), (626, 117), (580, 37)),
        (0,), (1,), (0, 1)),
    Branch("east_drop_splay", 2, (
        (880, 496), (822, 570), (847, 641)),
        (0,), (1,), (0, 1)),
    Branch("central_spectral_rise", 2, (
        (566, 398), (552, 280), (492, 239), (513, 139), (470, 83)),
        (0, 2), (1, 3), (0, 2, 3)),
)


def _mask() -> np.ndarray:
    return np.zeros((WORK, WORK), np.float32)


def _f(a: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(a, np.float32), 0.0, 1.0)


def _rgb(value: str) -> np.ndarray:
    value = value.lstrip("#")
    return np.asarray(tuple(int(value[i:i + 2], 16) / 255.0
                            for i in (0, 2, 4)), np.float32)


def _line(dst: np.ndarray, a, b, width: int, value: float) -> None:
    cv2.line(dst, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
             float(value), max(4, min(16, int(width))), cv2.LINE_AA)


def _poly(dst: np.ndarray, points, value: float, fill: bool = True,
          width: int = 4) -> None:
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32)
    if fill:
        cv2.fillPoly(dst, [pts], float(value), cv2.LINE_AA)
    else:
        cv2.polylines(dst, [pts], True, float(value),
                      max(4, min(16, int(width))), cv2.LINE_AA)


def _circle(dst: np.ndarray, center, radius: float, value: float) -> None:
    cv2.circle(dst, tuple(np.rint(center).astype(int)),
               max(4, min(16, int(round(radius)))), float(value), -1,
               cv2.LINE_AA)


def _blend(paint: np.ndarray, color: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    a = np.clip(alpha, 0.0, 1.0)[..., None]
    return paint * (1.0 - a) + color * a


def _unit(v: np.ndarray) -> np.ndarray:
    return v / (float(np.linalg.norm(v)) + 1e-6)


def _normal(v: np.ndarray) -> np.ndarray:
    u = _unit(v)
    return np.asarray((-u[1], u[0]), np.float32)


def _tier_value(branch_index: int, segment_index: int, salt: int = 0) -> Tuple[int, float]:
    tier = (branch_index * 5 + segment_index * 3
            + branch_index * segment_index + salt) % 8
    return tier, .12 + .87 * tier / 7.0


def _paint_tiers(paint: np.ndarray, mask: np.ndarray, tone: np.ndarray,
                 colors: Sequence[str], opacity: float) -> np.ndarray:
    palette = np.asarray([_rgb(color) for color in colors], np.float32)
    index = np.minimum(7, np.floor(_f(tone) * 7.999).astype(np.int16))
    color_image = palette[index]
    alpha = opacity * _f(mask)
    return paint * (1.0 - alpha[..., None]) + color_image * alpha[..., None]


def _tier_write(base: int, layers: Sequence[Tuple[np.ndarray, Sequence[int]]]) -> np.ndarray:
    out = np.full((WORK, WORK), float(base), np.float32)
    for tone, values in layers:
        palette = np.asarray(tuple(values), np.float32)
        if palette.size != 8:
            raise ValueError("every mineral material family requires eight shades")
        index = np.minimum(7, np.floor(_f(tone) * 7.999).astype(np.int16))
        active = tone > .02
        out[active] = palette[index[active]]
    return np.clip(out, 0, 255).astype(np.uint8)


def _spectrolite_continuum() -> Grammar:
    host_seam = _mask()
    mineral_core = _mask()
    cleavage_shoulders = _mask()
    angular_flash_windows = _mask()
    twin_offsets = _mask()
    fracture_ladders = _mask()
    exsolution_needles = _mask()
    terminated_fronts = _mask()
    shear_steps = _mask()
    wear_notches = _mask()
    schiller_film = _mask()
    tones = {name: _mask() for name in (
        "host", "core", "shoulder", "flash", "twin", "ladder", "needle",
        "front", "step", "wear", "film")}

    for branch_index, branch in enumerate(BRANCHES):
        points = np.asarray(branch.points, np.float32)
        order = branch.order
        core_width = (10, 8, 6)[order]
        host_width = (16, 14, 12)[order]
        shoulder_width = (6, 5, 4)[order]

        for segment_index, (a, b) in enumerate(zip(points[:-1], points[1:])):
            vector = b - a
            length = float(np.linalg.norm(vector))
            tangent = _unit(vector)
            normal = _normal(vector)
            tier, tone = _tier_value(branch_index, segment_index)
            side = -1.0 if (branch_index + segment_index) & 1 else 1.0

            _line(host_seam, a, b, host_width, .44 + .42 * tier / 7)
            _line(tones["host"], a, b, host_width, tone)
            _line(mineral_core, a, b, core_width, .58 + .39 * tier / 7)
            _line(tones["core"], a, b, core_width, tone)

            # A shoulder occupies one physically selected cleavage side.  It is
            # interrupted near joints rather than forming two generic outlines.
            sa = a + vector * .10 + normal * side * (7 + 2 * order)
            sb = a + vector * .84 + normal * side * (7 + 2 * order)
            _line(cleavage_shoulders, sa, sb, shoulder_width,
                  .54 + .40 * ((tier + 2) % 8) / 7)
            _line(tones["shoulder"], sa, sb, shoulder_width,
                  .12 + .87 * ((tier + 2) % 8) / 7)

            # Schiller is an asymmetric optical film on the opposite shoulder.
            fa = a + vector * .18 - normal * side * (5 + order)
            fb = a + vector * .72 - normal * side * (5 + order)
            _line(schiller_film, fa, fb, 4, .62 + .34 * ((tier + 5) % 8) / 7)
            _line(tones["film"], fa, fb, 4,
                  .12 + .87 * ((tier + 5) % 8) / 7)

            if segment_index in branch.twin_segments and length > 38:
                offset = normal * side * (13 + 2 * order)
                ta = a + vector * .18 + offset
                tb = a + vector * .78 + offset
                _line(twin_offsets, ta, tb, max(4, core_width - 3),
                      .60 + .36 * ((tier + 3) % 8) / 7)
                _line(tones["twin"], ta, tb, max(4, core_width - 3),
                      .12 + .87 * ((tier + 3) % 8) / 7)

                # Nonuniform local rungs link one twin slip only.  Rung counts
                # depend on physical segment length and branch order.
                fractions = ((.24, .43, .67) if order == 0
                             else ((.31, .58) if order == 1 else (.46,)))
                for rung_index, fraction in enumerate(fractions):
                    root = a + vector * fraction
                    tip = root + offset * (.78 + .08 * rung_index)
                    rtier, rtone = _tier_value(branch_index, segment_index,
                                               2 + rung_index)
                    _line(fracture_ladders, root, tip, 4,
                          .58 + .37 * rtier / 7)
                    _line(tones["ladder"], root, tip, 4, rtone)

                # Two shear steps explain how the parallel twin was displaced.
                for step_index, root in enumerate((ta, tb)):
                    step_tip = root - offset * .56 + tangent * (5 - 2 * step_index)
                    stier, stone = _tier_value(branch_index, segment_index,
                                               5 + step_index)
                    _line(shear_steps, root, step_tip, 4,
                          .60 + .35 * stier / 7)
                    _line(tones["step"], root, step_tip, 4, stone)

            if segment_index in branch.needle_segments and length > 28:
                count = 2 + ((branch_index + segment_index + order) % 4)
                for needle_index in range(count):
                    fraction = (.21 + .57 * (needle_index + 1) / (count + 1)
                                + .035 * np.sin(branch_index + needle_index))
                    root = a + vector * fraction
                    needle_side = side if needle_index & 1 else -side
                    angle_tangent = tangent * (3 + (needle_index % 3))
                    needle_length = 7 + ((branch_index * 3 + segment_index
                                          + needle_index * 5) % 9)
                    tip = root + normal * needle_side * needle_length + angle_tangent
                    ntier, ntone = _tier_value(branch_index, segment_index,
                                               3 * needle_index + 1)
                    _line(exsolution_needles, root, tip, 4,
                          .58 + .38 * ntier / 7)
                    _line(tones["needle"], root, tip, 4, ntone)

            # Cross-cut wear is attached only to selected older core segments.
            if (branch_index * 3 + segment_index * 5 + order) % 7 in (1, 4):
                fraction = .38 + .19 * ((branch_index + segment_index) % 3)
                center = a + vector * fraction
                half = 5 + ((branch_index + 2 * segment_index) % 6)
                wa, wb = center - normal * half, center + normal * half
                wtier, wtone = _tier_value(branch_index, segment_index, 6)
                _line(wear_notches, wa, wb, 4, .58 + .37 * wtier / 7)
                _line(tones["wear"], wa, wb, 4, wtone)

        # Joint-derived flash windows have no reusable stamp geometry: every
        # quadrilateral is solved from that joint's incoming/outgoing cleavage.
        for joint_index in branch.flash_joints:
            if not 0 < joint_index < len(points) - 1:
                continue
            previous, joint, following = points[joint_index - 1:joint_index + 2]
            incoming = _unit(joint - previous)
            outgoing = _unit(following - joint)
            n_in, n_out = _normal(incoming), _normal(outgoing)
            tier, tone = _tier_value(branch_index, joint_index, 4)
            side = -1.0 if (branch_index + joint_index) & 1 else 1.0
            span = 9 + ((branch_index * 3 + joint_index * 5) % 7)
            window = np.asarray((
                joint + incoming * 3 + n_in * side * 5,
                joint + incoming * span + n_in * side * (10 + order),
                joint + outgoing * span + n_out * side * (8 + 2 * order),
                joint + outgoing * 3 + n_out * side * 4,
            ), np.float32)
            _poly(angular_flash_windows, window,
                  .58 + .39 * tier / 7, True)
            _poly(tones["flash"], window, tone, True)
            # The film rim is physically separate from the colored window.
            _poly(schiller_film, window, .62 + .34 * ((tier + 2) % 8) / 7,
                  False, 4)
            _poly(tones["film"], window,
                  .12 + .87 * ((tier + 2) % 8) / 7, False, 4)

        # Every non-master branch has one unique terminated cleavage front.
        if branch_index:
            endpoint = points[-1]
            incoming = _unit(endpoint - points[-2])
            base_angle = float(np.degrees(np.arctan2(incoming[1], incoming[0])))
            fan_count = 2 + ((branch_index + order) % 4)
            for fan_index in range(fan_count):
                angle = np.deg2rad(base_angle - 43 + 86 * (fan_index + 1)
                                   / (fan_count + 1)
                                   + 7 * np.sin(branch_index * .7 + fan_index))
                direction = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
                length = 7 + ((branch_index * 5 + fan_index * 3) % 9)
                ftier, ftone = _tier_value(branch_index, fan_index, 7)
                _line(terminated_fronts, endpoint, endpoint + direction * length,
                      4, .58 + .38 * ftier / 7)
                _line(tones["front"], endpoint, endpoint + direction * length,
                      4, ftone)
            _circle(shear_steps, endpoint, 4 + (branch_index % 3), .72)
            _circle(tones["step"], endpoint, 4 + (branch_index % 3),
                    .12 + .87 * ((branch_index * 3) % 8) / 7)

    marks = (
        ("connected_host_seam", _f(host_seam), "N"),
        ("spectrolite_mineral_core", _f(mineral_core), "A"),
        ("asymmetric_cleavage_shoulders", _f(cleavage_shoulders), "B"),
        ("joint_solved_angular_flash_windows", _f(angular_flash_windows), "A"),
        ("local_twin_offsets", _f(twin_offsets), "B"),
        ("branch_order_fracture_ladders", _f(fracture_ladders), "B"),
        ("attached_exsolution_needles", _f(exsolution_needles), "A"),
        ("unique_terminated_fronts", _f(terminated_fronts), "B"),
        ("twin_shear_steps", _f(shear_steps), "A"),
        ("cross_cut_fracture_wear", _f(wear_notches), "B"),
        ("asymmetric_schiller_film", _f(schiller_film), "A"),
    )

    paint = np.broadcast_to(_rgb("#030610"), (WORK, WORK, 3)).copy()
    paint = _paint_tiers(paint, marks[0][1], tones["host"],
                         ("#071225", "#091831", "#0b203c", "#102544",
                          "#17284b", "#1b2d55", "#22345f", "#2a3967"), .84)
    paint = _paint_tiers(paint, marks[1][1], tones["core"],
                         ("#1238a8", "#185fda", "#168ee4", "#12c7d8",
                          "#22e3b0", "#92e849", "#e8d943", "#fff0a0"), .95)
    paint = _paint_tiers(paint, marks[2][1], tones["shoulder"],
                         ("#32176e", "#51229d", "#7133c3", "#913ed0",
                          "#b34bc6", "#d05ea0", "#e47772", "#f59b53"), .91)
    paint = _paint_tiers(paint, marks[3][1], tones["flash"],
                         ("#0b6aff", "#05a7ff", "#00e1dd", "#23f29c",
                          "#a7f247", "#f5d93b", "#ff8a38", "#ff4bc4"), .96)
    paint = _paint_tiers(paint, marks[4][1], tones["twin"],
                         ("#3525af", "#563de0", "#7c48ef", "#a64be4",
                          "#cc4dcc", "#eb5b98", "#fb7565", "#ffae45"), .94)
    paint = _paint_tiers(paint, marks[5][1], tones["ladder"],
                         ("#0d7f8f", "#0aaeb1", "#0ad3bd", "#20efac",
                          "#69f183", "#a6ef5d", "#dbea52", "#fff082"), .92)
    paint = _paint_tiers(paint, marks[6][1], tones["needle"],
                         ("#1664dd", "#137cfa", "#12a9ff", "#18d5f0",
                          "#35f0ca", "#78f49a", "#bef46d", "#f5f49b"), .96)
    paint = _paint_tiers(paint, marks[7][1], tones["front"],
                         ("#5c1fa9", "#7b2ac6", "#9d37d5", "#bf42d1",
                          "#db4caf", "#ef5e80", "#f5795c", "#ffa84c"), .94)
    paint = _paint_tiers(paint, marks[8][1], tones["step"],
                         ("#1679ae", "#179ec0", "#1ac6c6", "#31e0b7",
                          "#69e99d", "#a5ed7e", "#dbe96d", "#fff39a"), .95)
    paint = _paint_tiers(paint, marks[9][1], tones["wear"],
                         ("#b12454", "#cf2d62", "#e63d6c", "#f45172",
                          "#fa6d75", "#ff8d75", "#ffb06f", "#ffd783"), .93)
    paint = _paint_tiers(paint, marks[10][1], tones["film"],
                         ("#1f55d6", "#287bea", "#2ca4ec", "#30cedd",
                          "#48e8bc", "#7be892", "#b8e872", "#eceb8a"), .72)

    # Independent material ancestry:
    # M = mineral core / flash precipitate / needles.
    # R = cleavage wear / ladders / terminated fronts.
    # Cc = asymmetric schiller film / twin offsets / shear steps.
    metal = _tier_write(9, (
        (tones["core"], (44, 70, 98, 128, 160, 192, 224, 252)),
        (tones["flash"], (62, 90, 120, 150, 180, 208, 234, 255)),
        (tones["needle"], (36, 64, 94, 126, 158, 190, 222, 250)),
    ))
    rough = _tier_write(232, (
        (tones["shoulder"], (216, 190, 164, 138, 112, 84, 54, 22)),
        (tones["ladder"], (202, 176, 150, 124, 98, 72, 44, 16)),
        (tones["front"], (224, 196, 168, 140, 112, 82, 50, 18)),
        (tones["wear"], (236, 204, 172, 140, 108, 76, 44, 12)),
    ))
    coat = _tier_write(8, (
        (tones["film"], (52, 82, 112, 142, 172, 202, 230, 254)),
        (tones["twin"], (38, 68, 100, 132, 164, 196, 226, 252)),
        (tones["step"], (64, 94, 124, 154, 184, 212, 238, 255)),
        (tones["flash"], (44, 74, 104, 134, 164, 194, 224, 250)),
    ))

    hue_null = np.full((WORK, WORK), .025, np.float32)
    levels = (.11, .88, .42, .98, .57, .73, .92, .48, .83, .34, .77)
    for (_name, mask, _bank), level in zip(marks, levels):
        hue_null = hue_null * (1.0 - mask) + level * mask
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    if any(float(mask.std()) < .001 for _name, mask, _bank in marks):
        raise ValueError("spectrolite continuum has an absent causal mark")
    if any(len(np.unique(channel)) < 8 or float(channel.std()) < 15
           for channel in (metal, rough, coat)):
        raise ValueError("spectrolite continuum has a weak material channel")
    return Grammar(marks, _f(paint), hue_null, (metal, rough, coat),
                   "one globally connected branching spectrolite seam with branch-order mineral anatomy",
                   tuple(branch.name for branch in BRANCHES))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {ID: _spectrolite_continuum}
CANDIDATE_IDS: Tuple[str, ...] = ()


@lru_cache(maxsize=1)
def _authored(fid: str) -> Tuple[np.ndarray, np.ndarray]:
    grammar = BUILDERS[fid]()
    return grammar.paint, np.stack(grammar.explicit_spec, axis=2).astype(np.uint8)


def clear_cache() -> None:
    _authored.cache_clear()


def debug_grammar(fid: str = ID) -> Grammar:
    return BUILDERS[fid]()


def owner_unions(grammar: Grammar) -> Dict[str, np.ndarray]:
    unions = {key: np.zeros((WORK, WORK), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        unions[bank] = np.maximum(unions[bank], mask)
    return unions


def debug_angle_pair(fid: str = ID) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    paint, spec = _authored(fid)
    owners = owner_unions(debug_grammar(fid))
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - .60 * rough, .18, 1.0)
    gain_a = np.clip(.10 + 1.12 * metal * aperture
                     + .62 * owners["A"] - .25 * owners["B"], .05, 1.42)
    gain_b = np.clip(.10 + 1.12 * coat * aperture
                     + .62 * owners["B"] - .25 * owners["A"], .05, 1.42)
    blue_green = np.asarray((.015, .18, .52), np.float32)
    gold_magenta = np.asarray((.43, .07, .27), np.float32)
    angle_a = np.clip(paint * gain_a[..., None]
                      + blue_green * (owners["A"] * aperture)[..., None], 0, 1)
    angle_b = np.clip(paint * gain_b[..., None]
                      + gold_magenta * (owners["B"] * aperture)[..., None], 0, 1)
    return (angle_a.astype(np.float32), angle_b.astype(np.float32),
            np.abs(angle_a - angle_b).astype(np.float32))


def render_native(fid: str = ID, size: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
    paint, spec = _authored(fid)
    if size == WORK:
        return paint.copy(), spec.copy()
    paint = cv2.resize(paint, (size, size), interpolation=cv2.INTER_CUBIC)
    spec = cv2.resize(spec, (size, size), interpolation=cv2.INTER_NEAREST)
    return _f(paint), spec.astype(np.uint8)


def _entry(fid: str = ID):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        h, w = int(shape[0]), int(shape[1])
        source = np.asarray(paint, np.float32)
        if source.ndim != 3 or source.shape[2] < 3:
            source = np.zeros((h, w, 3), np.float32)
        else:
            source = source[:, :, :3]
            if source.size and float(source.max()) > 1.5:
                source = source / 255.0
            if source.shape[:2] != (h, w):
                source = cv2.resize(source, (w, h), interpolation=cv2.INTER_LINEAR)
        zone = np.asarray(mask, np.float32)
        if zone.ndim == 3:
            zone = zone[:, :, 0]
        if zone.shape != (h, w):
            zone = cv2.resize(zone, (w, h), interpolation=cv2.INTER_LINEAR)
        authored, _spec = render_native(fid, max(h, w))
        if authored.shape[:2] != (h, w):
            authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_CUBIC)
        alpha = np.clip(zone * max(0.0, float(pm)), 0, 1)[..., None]
        return np.clip(source * (1.0 - alpha) + authored * alpha, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        h, w = int(shape[0]), int(shape[1])
        zone = np.asarray(mask, np.float32)
        if zone.ndim == 3:
            zone = zone[:, :, 0]
        if zone.shape != (h, w):
            zone = cv2.resize(zone, (w, h), interpolation=cv2.INTER_LINEAR)
        _paint, authored = render_native(fid, max(h, w))
        if authored.shape[:2] != (h, w):
            authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_NEAREST)
        active = np.clip(CALM_SPEC + (authored.astype(np.float32) - CALM_SPEC)
                         * max(0.0, float(sm)), 0, 255)
        alpha = np.clip(zone, 0, 1)[..., None]
        out = np.empty((h, w, 4), np.uint8)
        out[:, :, :3] = np.clip(active * alpha + CALM_SPEC * (1.0 - alpha),
                                0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return out
    return spec_fn, paint_fn


def install_into_engine(registry, base_registry=None):
    # Frozen negative study. Keep fail-closed even if imported accidentally.
    for fid in CANDIDATE_IDS:
        registry[fid] = _entry(fid)
    return "fractured-wilds-fullres-spectrolite-continuum: 0 rejected studies advanced"


__all__ = ["BRANCHES", "BUILDERS", "CALM_SPEC", "CANDIDATE_IDS", "Grammar",
           "ID", "_authored", "_entry", "clear_cache", "debug_angle_pair",
           "debug_grammar", "install_into_engine", "owner_unions",
           "render_native"]
