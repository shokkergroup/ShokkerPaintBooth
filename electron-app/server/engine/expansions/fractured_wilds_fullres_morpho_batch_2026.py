# -*- coding: utf-8 -*-
"""Four frozen, isolated native-2048 Fractured Morpho rejection studies.

This module is intentionally unwired.  It exists to answer the owner's
2026-08-24 correction that Fractured Wilds must be judged as 2048x2048 art,
not as picker thumbnails.  Each finish owns a different deterministic physical
construction and a different M/R/Cc construction.  No RNG, seeded texture,
FBM, grain, or noise is used anywhere in the image ancestry.

SPB-WILDS-FULLRES tick FR-M1, 2026-08-24.  Owner verdict addressed:
"biggest cardinal sin PERIOD ... EXACT SAME pattern just recolored or exact
same spec maps" and "2048x2048 canvas size images ... make REAL PROGRESS".
Metric movement is deliberately recorded as N/A -> REJECT: full-resolution eye
review found repeated micro-glyph/paver units in every study.  No M7, release,
or owner-acceptance claim is made.

Native doctrine:
* authored at 1024 and reconstructed at 2048 with analytic/cubic resampling;
* geometry is expressed in a 512-unit design space, then drawn at 2x; every
  stroke/rim/dot is 2--8 design units = 8--32 native pixels;
* every finish stacks at least six causally attached mark families;
* every material channel uses at least eight explicit intensity tiers;
* owner banks A/B are explicit, opposed, and independently inspectable.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Mapping, Sequence, Tuple

import cv2
import numpy as np


DESIGN = 512
S = 1024
DRAW_SCALE = S / DESIGN
CALM_SPEC = np.asarray((6.0, 176.0, 10.0), np.float32)


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    hue_null: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]
    mechanism: str
    primitive_native_px: Tuple[int, int] = (8, 32)


def _mask() -> np.ndarray:
    return np.zeros((S, S), np.float32)


def _f32(a: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(a, np.float32), 0.0, 1.0)


def _rgb(value: str) -> np.ndarray:
    value = value.lstrip("#")
    return np.asarray(tuple(int(value[i:i + 2], 16) / 255.0
                            for i in (0, 2, 4)), np.float32)


def _line(dst: np.ndarray, a, b, width: int, value: float = 1.0) -> None:
    cv2.line(dst, tuple(np.rint(np.asarray(a) * DRAW_SCALE).astype(int)),
             tuple(np.rint(np.asarray(b) * DRAW_SCALE).astype(int)),
             float(value), max(2, min(8, int(width))) * int(DRAW_SCALE), cv2.LINE_AA)


def _poly(dst: np.ndarray, points, value: float = 1.0,
          width: int = 2, fill: bool = True) -> None:
    pts = np.rint(np.asarray(points, np.float32) * DRAW_SCALE).astype(np.int32)
    stroke = max(2, min(8, int(width))) * int(DRAW_SCALE)
    if fill:
        cv2.fillPoly(dst, [pts], float(value), cv2.LINE_AA)
    else:
        cv2.polylines(dst, [pts], True, float(value), stroke, cv2.LINE_AA)


def _ellipse(dst: np.ndarray, center, axes, angle: float, value: float = 1.0,
             width: int = 2, fill: bool = False, start: float = 0.0,
             end: float = 360.0) -> None:
    cv2.ellipse(dst, tuple(np.rint(np.asarray(center) * DRAW_SCALE).astype(int)),
                tuple(max(2, min(8, int(round(v)))) * int(DRAW_SCALE) for v in axes),
                float(angle), float(start), float(end), float(value),
                -1 if fill else max(2, min(8, int(width))) * int(DRAW_SCALE), cv2.LINE_AA)


def _circle(dst: np.ndarray, center, radius: float, value: float = 1.0,
            fill: bool = True, width: int = 2) -> None:
    cv2.circle(dst, tuple(np.rint(np.asarray(center) * DRAW_SCALE).astype(int)),
               max(2, min(8, int(round(radius)))) * int(DRAW_SCALE), float(value),
               -1 if fill else max(2, min(8, int(width))) * int(DRAW_SCALE), cv2.LINE_AA)


def _blend(paint: np.ndarray, color: np.ndarray, alpha: np.ndarray | float) -> np.ndarray:
    a = np.clip(np.asarray(alpha, np.float32), 0.0, 1.0)
    if a.ndim == 2:
        a = a[..., None]
    return paint * (1.0 - a) + color * a


def _oriented(center, angle_deg: float, local_points) -> np.ndarray:
    pts = np.asarray(local_points, np.float32)
    angle = np.deg2rad(angle_deg)
    rotation = np.asarray(((np.cos(angle), -np.sin(angle)),
                           (np.sin(angle), np.cos(angle))), np.float32)
    return pts @ rotation.T + np.asarray(center, np.float32)


def _cubic(p0, p1, p2, p3, count: int = 241) -> np.ndarray:
    t = np.linspace(0.0, 1.0, count, dtype=np.float32)[:, None]
    omt = 1.0 - t
    return (omt ** 3 * np.asarray(p0, np.float32)
            + 3.0 * omt ** 2 * t * np.asarray(p1, np.float32)
            + 3.0 * omt * t ** 2 * np.asarray(p2, np.float32)
            + t ** 3 * np.asarray(p3, np.float32))


def _tier_write(base: int, layers: Sequence[Tuple[np.ndarray, Sequence[int]]]) -> np.ndarray:
    """Write deterministic eight-shade material tiers without a noise carrier."""
    out = np.full((S, S), float(base), np.float32)
    for mask, values in layers:
        palette = np.asarray(tuple(values), np.float32)
        if palette.size != 8:
            raise ValueError("material families must provide exactly eight shades")
        tier = np.minimum(7, np.floor(_f32(mask) * 7.999).astype(np.int16))
        active = mask > .015
        out[active] = palette[tier[active]]
    return np.clip(out, 0, 255).astype(np.uint8)


def _hue_null_from_marks(marks, levels: Sequence[float]) -> np.ndarray:
    out = np.full((S, S), .035, np.float32)
    for (_name, mask, _bank), level in zip(marks, levels):
        out = out * (1.0 - mask) + float(level) * mask
    return np.repeat(_f32(out)[..., None], 3, axis=2)


def _validate(grammar: Grammar) -> Grammar:
    names = [name for name, _mask_value, _bank in grammar.marks]
    if len(names) < 6 or len(names) != len(set(names)):
        raise ValueError("finish must own at least six distinct semantic marks")
    if {bank for _name, _mask_value, bank in grammar.marks} < {"A", "B"}:
        raise ValueError("finish lacks explicit opposed A/B ownership")
    for name, mask, _bank in grammar.marks:
        if float(np.std(mask)) < .002 or float(np.max(mask)) < .20:
            raise ValueError(f"flat or absent semantic family: {name}")
    for channel in grammar.explicit_spec:
        if len(np.unique(channel)) < 8 or float(np.std(channel)) < 12.0:
            raise ValueError("material channel lacks shade range")
    return grammar


def _build_sunset_moth() -> Grammar:
    """Wing-vein rivers carrying hooked, fractured diffraction blades."""
    vein_rivers = _mask()
    lamellar_blades = _mask()
    blade_hollows = _mask()
    cross_stitches = _mask()
    branch_spurs = _mask()
    distal_chips = _mask()
    junction_beads = _mask()
    recoil_scars = _mask()
    tone_vein = _mask()
    tone_blade = _mask()
    tone_hollow = _mask()
    tone_stitch = _mask()
    tone_spur = _mask()
    tone_chip = _mask()
    tone_bead = _mask()
    tone_scar = _mask()

    # Dense deterministic wing-flow fabric.  The analytic field controls the
    # local direction and which anatomy physically exists; it is never painted.
    # This replaces the rejected row/rail prototype with thousands of attached
    # 8--32 px blade, hollow, tie, fork, chip, bead and recoil primitives.
    for row in range(-2, 51):
        for col in range(-2, 58):
            cx = col * 9.35 + (row & 1) * 4.55 + 2.35 * np.sin(.29 * row + .17 * col)
            cy = row * 10.45 + 2.15 * np.cos(.23 * col - .31 * row)
            center = np.asarray((cx, cy), np.float32)
            phase = (np.sin(2 * np.pi * (cx / 181.0 + .17 * np.sin(cy / 83.0)))
                     + .72 * np.cos(2 * np.pi * (cy / 227.0 - cx / 613.0)))
            state = int(np.digitize(phase, (-.92, -.28, .34, .98)))
            tier = (row * 7 + col * 5 + row * col) % 8
            angle = (18.0 + 34.0 * np.sin(2 * np.pi * cy / 263.0)
                     - 29.0 * np.cos(2 * np.pi * cx / 317.0)
                     + 11.0 * np.sin((row + col) * .21))
            level = .56 + .41 * tier / 7
            tone = .11 + .88 * tier / 7
            t = np.asarray((np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))), np.float32)
            n = np.asarray((-t[1], t[0]), np.float32)

            # A broken local vein segment anchors every scale without creating
            # one full-card macro rail.
            _line(vein_rivers, center - t * 3.8, center + t * 3.8, 2, level)
            _line(tone_vein, center - t * 3.8, center + t * 3.8, 2, tone)
            side = -1.0 if (row + col) & 1 else 1.0
            blade_center = center + n * side * (2.5 + .35 * (state % 3))
            blade_angle = angle + side * (42 + 5 * state)
            blade = _oriented(blade_center, blade_angle,
                              ((-3.6, 0), (-1.0, -1.8), (3.8, -.7),
                               (4.5, 0), (3.8, .7), (-1.0, 1.8)))
            _poly(lamellar_blades, blade, level)
            _poly(tone_blade, blade, tone)

            if state in (0, 3):
                a, b = _oriented(blade_center, blade_angle, ((-2.8, 0), (2.9, 0)))
                _line(blade_hollows, a, b, 2, .60 + .35 * tier / 7)
                _line(tone_hollow, a, b, 2,
                      .11 + .88 * ((tier + 3) % 8) / 7)
            if state in (1, 4):
                _line(cross_stitches, center - n * 3.9, center + n * 3.9,
                      2, .60 + .35 * tier / 7)
                _line(tone_stitch, center - n * 3.9, center + n * 3.9,
                      2, .11 + .88 * ((tier + 2) % 8) / 7)
            if state == 2:
                root = center - t * 2.2
                for fork_side in (-1, 1):
                    tip = root + t * 4.7 + n * fork_side * 3.0
                    _line(branch_spurs, root, tip, 2, .60 + .35 * tier / 7)
                    _line(tone_spur, root, tip, 2,
                          .11 + .88 * ((tier + fork_side + 3) % 8) / 7)
            if state == 3:
                tip = blade[3]
                chip = _oriented(tip, blade_angle,
                                 ((-.5, -1.6), (3.0, 0), (-.5, 1.6)))
                _poly(distal_chips, chip, .64 + .31 * tier / 7)
                _poly(tone_chip, chip, .11 + .88 * ((tier + 5) % 8) / 7)
            if state == 4:
                _circle(junction_beads, center, 2.0 + .3 * (tier % 3),
                        .66 + .30 * tier / 7)
                _circle(tone_bead, center, 2.0 + .3 * (tier % 3),
                        .11 + .88 * ((tier + 1) % 8) / 7)
            if state in (0, 2):
                slash_a, slash_b = _oriented(center - n * side * 2.6,
                                             angle - side * 47,
                                             ((-3.5, 0), (3.5, 0)))
                _line(recoil_scars, slash_a, slash_b, 2, .62 + .33 * tier / 7)
                _line(tone_scar, slash_a, slash_b, 2,
                      .11 + .88 * ((tier + 6) % 8) / 7)

    marks = (
        ("wing_vein_rivers", _f32(vein_rivers), "B"),
        ("hooked_lamellar_blades", _f32(lamellar_blades), "A"),
        ("blade_optical_hollows", _f32(blade_hollows), "B"),
        ("cross_vein_stitches", _f32(cross_stitches), "A"),
        ("inter_river_branch_spurs", _f32(branch_spurs), "B"),
        ("fractured_distal_chips", _f32(distal_chips), "A"),
        ("vein_junction_beads", _f32(junction_beads), "B"),
        ("branch_recoil_scars", _f32(recoil_scars), "A"),
    )
    paint = np.broadcast_to(_rgb("#09051f"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#5b123f"), .72 * marks[0][1])
    paint = _blend(paint, _rgb("#ff5038"), .90 * marks[1][1])
    paint = _blend(paint, _rgb("#ffd43b"), .92 * marks[2][1])
    paint = _blend(paint, _rgb("#05dba8"), .94 * marks[3][1])
    paint = _blend(paint, _rgb("#167cf3"), .90 * marks[4][1])
    paint = _blend(paint, _rgb("#ff29bc"), .92 * marks[5][1])
    paint = _blend(paint, _rgb("#baff4d"), .94 * marks[6][1])
    paint = _blend(paint, _rgb("#8a3dff"), .91 * marks[7][1])
    paint = _blend(paint, _rgb("#fff0b0"), .36 * tone_blade * marks[1][1])
    paint = _blend(paint, _rgb("#22fff0"), .30 * tone_stitch * marks[3][1])

    # Unique Sunset material: metal follows blade ancestry, roughness records
    # hollows/stitches, and clearcoat follows the branching vascular fabric.
    metal = _tier_write(10, (
        (tone_blade, (54, 82, 112, 142, 174, 204, 232, 252)),
        (tone_chip, (72, 98, 126, 154, 184, 212, 238, 255)),
        (tone_scar, (28, 58, 90, 122, 156, 190, 222, 248)),
    ))
    rough = _tier_write(228, (
        (tone_vein, (210, 188, 166, 144, 122, 98, 72, 46)),
        (tone_hollow, (196, 170, 144, 118, 92, 68, 42, 18)),
        (tone_stitch, (182, 156, 132, 108, 82, 58, 34, 12)),
    ))
    coat = _tier_write(14, (
        (tone_spur, (42, 70, 100, 132, 164, 194, 224, 250)),
        (tone_bead, (68, 96, 126, 158, 188, 216, 240, 255)),
        (tone_vein, (34, 60, 88, 120, 152, 184, 218, 246)),
    ))
    return _validate(Grammar(marks, _f32(paint),
                             _hue_null_from_marks(marks,
                                                   (.31, .92, .56, .78, .42, .86, .66, .97)),
                             (metal, rough, coat),
                             "fractured wing-vein rivers with hooked diffraction blades"))


def _build_atlas_wing() -> Grammar:
    """A topographic atlas of five alternating micro-fenestra anatomies."""
    hollow_kites = _mask()
    split_pennants = _mask()
    tripod_windows = _mask()
    broken_hooks = _mask()
    folded_fans = _mask()
    coordinate_ticks = _mask()
    suture_bridges = _mask()
    route_beacons = _mask()
    tones = {name: _mask() for name in
             ("kite", "pennant", "tripod", "hook", "fan", "tick", "bridge", "beacon")}
    centers: Dict[Tuple[int, int], np.ndarray] = {}
    states: Dict[Tuple[int, int], int] = {}

    for row in range(-1, 38):
        for col in range(-1, 39):
            cx = col * 14.1 + (row & 1) * 6.7 + 2.2 * np.sin(.31 * row + .17 * col)
            cy = row * 14.35 + 2.0 * np.cos(.23 * col - .29 * row)
            center = np.asarray((cx, cy), np.float32)
            # Coherent anatomical territories replace the rejected confetti
            # alternation.  The phase selects anatomy but never reaches paint.
            phase = (np.sin(2 * np.pi * (cx / 211.0 + .13 * np.sin(cy / 77.0)))
                     + .68 * np.cos(2 * np.pi * (cy / 247.0 - cx / 701.0)))
            state = int(np.digitize(phase, (-.92, -.29, .31, .96)))
            tier = (7 * row + 5 * col + row * col) % 8
            angle = (22 + 31 * np.sin(2 * np.pi * cy / 279.0)
                     - 27 * np.cos(2 * np.pi * cx / 331.0)
                     + 7 * np.sin(.4 * (row + col))) % 180
            centers[(row, col)] = center
            states[(row, col)] = state
            level = .54 + .42 * tier / 7
            tone = .11 + .88 * tier / 7

            if state == 0:
                pts = _oriented(center, angle, ((0, -3.9), (3.7, 0),
                                                 (0, 3.3), (-2.8, 0)))
                _poly(hollow_kites, pts, level, 2, False)
                _poly(tones["kite"], pts, tone, 2, False)
                cut_a, cut_b = _oriented(center, angle, ((-2.5, 0), (2.8, 0)))
                _line(coordinate_ticks, cut_a, cut_b, 2, .64)
                _line(tones["tick"], cut_a, cut_b, 2, .13 + .86 * ((tier + 3) % 8) / 7)
            elif state == 1:
                left = _oriented(center, angle, ((-3.9, -3.1), (-.5, 0), (-3.8, 3.0)))
                right = _oriented(center, angle, ((3.9, -2.5), (.5, 0), (3.7, 3.4)))
                _poly(split_pennants, left, level)
                _poly(split_pennants, right, .55 + .40 * ((tier + 2) % 8) / 7)
                _poly(tones["pennant"], left, tone)
                _poly(tones["pennant"], right, .11 + .88 * ((tier + 2) % 8) / 7)
            elif state == 2:
                for spoke in (angle + 3, angle + 123, angle + 243):
                    a, b = _oriented(center, spoke, ((0, 0), (4.3, 0)))
                    _line(tripod_windows, a, b, 2, level)
                    _line(tones["tripod"], a, b, 2, tone)
                _circle(route_beacons, center, 2.0, .66 + .28 * tier / 7)
                _circle(tones["beacon"], center, 2.0, .11 + .88 * ((tier + 5) % 8) / 7)
            elif state == 3:
                _ellipse(broken_hooks, center, (4, 3), angle, level, 2, False, 25, 290)
                _ellipse(tones["hook"], center, (4, 3), angle, tone, 2, False, 25, 290)
                barb_a, barb_b = _oriented(center, angle + 25, ((2.2, -1.2), (4.5, -3.1)))
                _line(coordinate_ticks, barb_a, barb_b, 2, .68)
                _line(tones["tick"], barb_a, barb_b, 2, .11 + .88 * ((tier + 4) % 8) / 7)
            else:
                root = _oriented(center, angle, ((-3.8, 0),))[0]
                for fan_angle in (-34, -11, 13, 37):
                    tip = _oriented(root, angle + fan_angle, ((0, 0), (6.2, 0)))[1]
                    _line(folded_fans, root, tip, 2, level)
                    _line(tones["fan"], root, tip, 2,
                          .11 + .88 * ((tier + int((fan_angle + 40) / 12)) % 8) / 7)

    # Bridges only join unlike neighbouring anatomies: this is a map legend,
    # not an indiscriminate mesh/noise overlay.
    for key, center in centers.items():
        row, col = key
        for neighbour in ((row, col + 1), (row + 1, col)):
            other = centers.get(neighbour)
            if other is None or states[key] == states[neighbour]:
                continue
            if (row + 2 * col + states[key]) % 3 == 2:
                continue
            tier = (row * 5 + col * 3 + states[key]) % 8
            direction = other - center
            unit = direction / (np.linalg.norm(direction) + 1e-6)
            a, b = center + unit * 3.3, other - unit * 3.3
            _line(suture_bridges, a, b, 2, .56 + .40 * tier / 7)
            _line(tones["bridge"], a, b, 2, .11 + .88 * tier / 7)
            if tier in (1, 5):
                mid = (a + b) * .5
                _circle(route_beacons, mid, 2, .68 + .25 * tier / 7)
                _circle(tones["beacon"], mid, 2, .11 + .88 * ((tier + 2) % 8) / 7)

    marks = (
        ("hollow_cartographic_kites", _f32(hollow_kites), "A"),
        ("opposed_split_pennants", _f32(split_pennants), "B"),
        ("three_way_window_trusses", _f32(tripod_windows), "A"),
        ("broken_serpentine_hooks", _f32(broken_hooks), "B"),
        ("folded_atlas_fans", _f32(folded_fans), "A"),
        ("coordinate_edge_ticks", _f32(coordinate_ticks), "B"),
        ("unlike_anatomy_sutures", _f32(suture_bridges), "A"),
        ("route_junction_beacons", _f32(route_beacons), "B"),
    )
    paint = np.broadcast_to(_rgb("#12080d"), (S, S, 3)).copy()
    for mask, color, alpha in (
        (marks[0][1], "#ffc244", .92), (marks[1][1], "#e43826", .92),
        (marks[2][1], "#6af000", .90), (marks[3][1], "#00bda7", .93),
        (marks[4][1], "#f07e14", .91), (marks[5][1], "#9e36ff", .94),
        (marks[6][1], "#34d9ff", .94), (marks[7][1], "#fff2a3", .97)):
        paint = _blend(paint, _rgb(color), alpha * mask)
    paint = _blend(paint, _rgb("#ff4d93"), .32 * tones["pennant"] * marks[1][1])
    paint = _blend(paint, _rgb("#d8ff73"), .30 * tones["fan"] * marks[4][1])

    # Atlas material is explicitly categorical: each anatomy owns a distinct
    # response, while the three channels use different ancestry groupings.
    metal = _tier_write(18, (
        (tones["kite"], (42, 72, 104, 136, 168, 198, 228, 252)),
        (tones["pennant"], (62, 90, 120, 150, 180, 208, 234, 255)),
        (tones["fan"], (28, 56, 86, 118, 152, 186, 220, 246)),
    ))
    rough = _tier_write(238, (
        (tones["hook"], (206, 180, 154, 128, 102, 76, 50, 24)),
        (tones["tick"], (218, 190, 162, 136, 110, 82, 54, 18)),
        (tones["pennant"], (196, 168, 142, 116, 90, 64, 38, 12)),
    ))
    coat = _tier_write(10, (
        (tones["tripod"], (48, 78, 108, 138, 168, 198, 228, 254)),
        (tones["bridge"], (34, 64, 96, 128, 160, 192, 224, 250)),
        (tones["beacon"], (76, 106, 136, 166, 196, 222, 242, 255)),
    ))
    return _validate(Grammar(marks, _f32(paint),
                             _hue_null_from_marks(marks,
                                                   (.88, .34, .72, .48, .94, .58, .80, .99)),
                             (metal, rough, coat),
                             "five-state micro-fenestra atlas joined only across anatomy changes"))


def _delaunay_triangles(points: np.ndarray) -> Sequence[np.ndarray]:
    subdiv = cv2.Subdiv2D((0, 0, DESIGN, DESIGN))
    for x, y in points:
        if 1 <= x < DESIGN - 1 and 1 <= y < DESIGN - 1:
            subdiv.insert((float(x), float(y)))
    triangles = []
    for raw in subdiv.getTriangleList().reshape(-1, 3, 2):
        if np.all((raw[:, 0] >= 0) & (raw[:, 0] < DESIGN)
                  & (raw[:, 1] >= 0) & (raw[:, 1] < DESIGN)):
            triangles.append(raw.astype(np.float32))
    return triangles


def _build_glasswing() -> Grammar:
    """Quasiperiodic transparent triangulation with causal edge anatomy."""
    silk_trusses = _mask()
    fenestra_rims = _mask()
    transparent_panes = _mask()
    diffraction_combs = _mask()
    dew_nodes = _mask()
    fracture_notches = _mask()
    centroid_bridges = _mask()
    edge_scale_islands = _mask()
    tones = {name: _mask() for name in
             ("truss", "rim", "pane", "comb", "dew", "notch", "bridge", "island")}

    # A quasiperiodically displaced triangular lattice gives biological
    # irregularity without seeded randomness or noise ancestry.
    points = []
    for row in range(-1, 40):
        for col in range(-1, 41):
            x = col * 13.25 + (row & 1) * 6.55 + 1.75 * np.sin(.37 * row + .61 * col)
            y = row * 13.45 + 1.65 * np.cos(.53 * col - .29 * row)
            if 1 <= x < DESIGN - 1 and 1 <= y < DESIGN - 1:
                points.append((x, y))
    points_array = np.asarray(points, np.float32)
    triangles = _delaunay_triangles(points_array)

    for index, tri in enumerate(triangles):
        centroid = tri.mean(axis=0)
        tier = (index * 5 + int(centroid[0] // 17) + 3 * int(centroid[1] // 19)) % 8
        state = (index + int(centroid[0] // 31) + 2 * int(centroid[1] // 29)) % 7
        phase = (np.sin(2 * np.pi * (centroid[0] / 239.0
                                      + .15 * np.sin(centroid[1] / 71.0)))
                 + .70 * np.cos(2 * np.pi * (centroid[1] / 281.0
                                              - centroid[0] / 683.0)))
        tissue = phase > -.10
        inner = centroid + (tri - centroid) * .54
        level = .54 + .42 * tier / 7
        tone = .11 + .88 * tier / 7
        # Coherent glass windows intentionally interrupt the tissue.  The
        # analytic phase controls physical existence only; it is never painted.
        if tissue and state != 0:
            _poly(silk_trusses, tri, level, 2, False)
            _poly(tones["truss"], tri, tone, 2, False)
        if abs(phase + .10) < .32 or (tissue and state in (1, 4)):
            _poly(fenestra_rims, inner, .62 + .34 * tier / 7, 2, False)
            _poly(tones["rim"], inner, .11 + .88 * ((tier + 2) % 8) / 7, 2, False)
        if (not tissue and state in (1, 2, 5)) or (tissue and state == 5):
            _poly(transparent_panes, inner, .34 + .36 * tier / 7, 2, True)
            _poly(tones["pane"], inner, .11 + .88 * ((tier + 4) % 8) / 7, 2, True)
        if tissue and state == 3:
            longest = np.argmax([np.linalg.norm(tri[(i + 1) % 3] - tri[i]) for i in range(3)])
            a, b = tri[longest], tri[(longest + 1) % 3]
            direction = b - a
            normal = np.asarray((-direction[1], direction[0]), np.float32)
            normal /= np.linalg.norm(normal) + 1e-6
            for q in (.28, .50, .72):
                c = a * (1 - q) + b * q
                _line(diffraction_combs, c - normal * 3.6, c + normal * 3.6,
                      2, level)
                _line(tones["comb"], c - normal * 3.6, c + normal * 3.6,
                      2, .11 + .88 * ((tier + int(q * 10)) % 8) / 7)
        if tissue and state == 6:
            vertex = tri[(tier + index) % 3]
            _circle(edge_scale_islands, vertex * .68 + centroid * .32, 2.3,
                    .62 + .34 * tier / 7)
            _circle(tones["island"], vertex * .68 + centroid * .32, 2.3,
                    .11 + .88 * ((tier + 5) % 8) / 7)
        if tissue and index % 11 == 3:
            _circle(dew_nodes, tri[(index // 11) % 3], 2.0 + .35 * (tier % 3),
                    .64 + .32 * tier / 7)
            _circle(tones["dew"], tri[(index // 11) % 3], 2.0 + .35 * (tier % 3),
                    .11 + .88 * ((tier + 1) % 8) / 7)
        if (not tissue and state in (0, 4)) or abs(phase + .10) < .12:
            edge = index % 3
            a, b = tri[edge], tri[(edge + 1) % 3]
            midpoint = (a + b) * .5
            direction = b - a
            direction /= np.linalg.norm(direction) + 1e-6
            _line(fracture_notches, midpoint - direction * 3.7,
                  midpoint + direction * 3.7, 2, .66 + .29 * tier / 7)
            _line(tones["notch"], midpoint - direction * 3.7,
                  midpoint + direction * 3.7, 2, tone)
        if tissue and index % 13 == 7:
            edge_mid = (tri[0] + tri[1]) * .5
            _line(centroid_bridges, centroid, edge_mid, 2, .60 + .35 * tier / 7)
            _line(tones["bridge"], centroid, edge_mid, 2, tone)

    marks = (
        ("transparent_silk_trusses", _f32(silk_trusses), "B"),
        ("double_fenestra_rims", _f32(fenestra_rims), "A"),
        ("thin_film_glass_panes", _f32(transparent_panes), "A"),
        ("edge_diffraction_combs", _f32(diffraction_combs), "B"),
        ("truss_dew_nodes", _f32(dew_nodes), "B"),
        ("missing_edge_fracture_notches", _f32(fracture_notches), "A"),
        ("centroid_tension_bridges", _f32(centroid_bridges), "B"),
        ("residual_scale_islands", _f32(edge_scale_islands), "A"),
    )
    paint = np.broadcast_to(_rgb("#050d17"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#10304b"), .52 * marks[2][1])
    paint = _blend(paint, _rgb("#54d8d0"), .78 * marks[0][1])
    paint = _blend(paint, _rgb("#d8d3f5"), .84 * marks[1][1])
    paint = _blend(paint, _rgb("#2cff83"), .91 * marks[3][1])
    paint = _blend(paint, _rgb("#ff77e6"), .95 * marks[4][1])
    paint = _blend(paint, _rgb("#ff9f35"), .92 * marks[5][1])
    paint = _blend(paint, _rgb("#4a87ff"), .92 * marks[6][1])
    paint = _blend(paint, _rgb("#d5ff4b"), .94 * marks[7][1])
    paint = _blend(paint, _rgb("#b9d9ff"), .26 * tones["pane"] * marks[2][1])

    # Glasswing material: almost non-metal panes, mirror-clear trusses/rims,
    # and rough micro-combs.  Each channel has different physical ancestry.
    metal = _tier_write(8, (
        (tones["island"], (46, 72, 100, 128, 158, 188, 220, 248)),
        (tones["notch"], (28, 54, 82, 112, 144, 178, 214, 246)),
        (tones["dew"], (66, 94, 124, 154, 184, 212, 238, 255)),
    ))
    rough = _tier_write(214, (
        (tones["pane"], (196, 174, 152, 130, 108, 86, 62, 38)),
        (tones["comb"], (232, 202, 172, 142, 112, 82, 50, 20)),
        (tones["island"], (184, 158, 132, 106, 80, 56, 32, 12)),
    ))
    coat = _tier_write(20, (
        (tones["truss"], (72, 100, 130, 160, 190, 216, 240, 255)),
        (tones["rim"], (58, 88, 118, 148, 178, 208, 234, 252)),
        (tones["bridge"], (40, 70, 102, 134, 166, 198, 228, 250)),
        (tones["dew"], (92, 120, 148, 176, 204, 226, 244, 255)),
    ))
    return _validate(Grammar(marks, _f32(paint),
                             _hue_null_from_marks(marks,
                                                   (.86, .70, .28, .94, .99, .52, .80, .62)),
                             (metal, rough, coat),
                             "quasiperiodic glass fenestrae with truss-bound micro-anatomy"))


def _build_peacock_eye() -> Grammar:
    """Vector-streamed asymmetric micro-ocelli with ruptures and lashes."""
    outer_crescents = _mask()
    inner_crescents = _mask()
    split_pupils = _mask()
    radial_lashes = _mask()
    chain_beads = _mask()
    fork_bridges = _mask()
    teardrop_scales = _mask()
    rupture_slashes = _mask()
    tones = {name: _mask() for name in
             ("outer", "inner", "pupil", "lash", "bead", "bridge", "tear", "slash")}

    streams = []
    for lane in range(38):
        x0 = -18.0
        y0 = 4.0 + lane * 14.0 + 7 * np.sin(.8 * lane)
        path = _cubic((x0, y0),
                      (138, y0 + 44 * np.sin(.63 * lane + .4)),
                      (354, y0 - 49 * np.cos(.47 * lane + .2)),
                      (536, y0 + 17 * np.sin(1.3 * lane)), 321)
        streams.append(path)
        for slot, idx in enumerate(range(7, 315, 7 + (lane % 4))):
            center = path[idx]
            tangent = path[min(320, idx + 3)] - path[max(0, idx - 3)]
            angle = np.degrees(np.arctan2(tangent[1], tangent[0]))
            tier = (lane * 5 + slot * 3 + lane * slot) % 8
            phase = (np.sin(2 * np.pi * (center[0] / 173.0
                                          + .12 * np.sin(center[1] / 61.0)))
                     + .64 * np.cos(2 * np.pi * center[1] / 229.0))
            state = int(np.digitize(phase, (-.88, -.25, .32, .92)))
            level = .56 + .40 * tier / 7
            tone = .11 + .88 * tier / 7
            axes = (3 + (state % 2), 2 + ((state + 1) % 2))
            # The ocellus is deliberately open/asymmetric: no repeated bullseye.
            start, end = ((24, 302) if state in (0, 3) else (78, 338))
            _ellipse(outer_crescents, center, axes, angle, level, 2, False, start, end)
            _ellipse(tones["outer"], center, axes, angle, tone, 2, False, start, end)
            offset = _oriented(center, angle, ((1.0 if state & 1 else -1.0, .15),))[0]
            _ellipse(inner_crescents, offset, (2, 2), angle + 23,
                     .62 + .34 * tier / 7, 2, False, start + 28, end - 35)
            _ellipse(tones["inner"], offset, (2, 2), angle + 23,
                     .11 + .88 * ((tier + 2) % 8) / 7, 2, False, start + 28, end - 35)
            if state in (1, 2, 4):
                p0, p1 = _oriented(center, angle + 31,
                                    ((-2.8, -.2), (2.8, .2)))
                _line(split_pupils, p0, p1, 2, .64 + .32 * tier / 7)
                _line(tones["pupil"], p0, p1, 2,
                      .11 + .88 * ((tier + 4) % 8) / 7)
            if (slot + lane) % 3 == 0:
                for lash_angle in (-58, -22, 38):
                    a, b = _oriented(center, angle + lash_angle,
                                     ((3.0, 0), (6.1, 0)))
                    _line(radial_lashes, a, b, 2, .60 + .35 * tier / 7)
                    _line(tones["lash"], a, b, 2,
                          .11 + .88 * ((tier + int((lash_angle + 60) / 20)) % 8) / 7)
            if (slot + 2 * lane) % 4 == 1:
                bead_center = _oriented(center, angle + 90, ((0, 3.5),))[0]
                _circle(chain_beads, bead_center, 2.0, .68 + .27 * tier / 7)
                _circle(tones["bead"], bead_center, 2.0,
                        .11 + .88 * ((tier + 6) % 8) / 7)
            if state == 4:
                tear = _oriented(center, angle - 28,
                                 ((-3.2, 0), (0, -2.1), (3.8, 0), (0, 1.7)))
                _poly(teardrop_scales, tear, .58 + .38 * tier / 7)
                _poly(tones["tear"], tear, .11 + .88 * ((tier + 1) % 8) / 7)
            if (slot + lane) % 7 == 2:
                a, b = _oriented(center, angle - 42, ((-3.6, 0), (3.6, 0)))
                _line(rupture_slashes, a, b, 2, .66 + .28 * tier / 7)
                _line(tones["slash"], a, b, 2,
                      .11 + .88 * ((tier + 5) % 8) / 7)

    # Forks tie adjacent streams only at sparse ocellus contacts.
    for lane in range(len(streams) - 1):
        for n, idx in enumerate((34, 82, 131, 180, 229, 278)):
            if (lane + n) % 3 == 1:
                continue
            a = streams[lane][idx]
            b = streams[lane + 1][min(320, idx + 5 * ((n % 3) - 1))]
            mid = (a + b) * .5 + np.asarray((3.5 * np.sin(lane + n), 0), np.float32)
            tier = (lane * 7 + n * 3) % 8
            _line(fork_bridges, a, mid, 2, .58 + .38 * tier / 7)
            _line(fork_bridges, mid, b, 2, .58 + .38 * tier / 7)
            _line(tones["bridge"], a, mid, 2, .11 + .88 * tier / 7)
            _line(tones["bridge"], mid, b, 2, .11 + .88 * tier / 7)

    marks = (
        ("asymmetric_outer_ocellus_crescents", _f32(outer_crescents), "A"),
        ("displaced_inner_crescents", _f32(inner_crescents), "B"),
        ("fractured_split_pupils", _f32(split_pupils), "B"),
        ("directional_ocellus_lashes", _f32(radial_lashes), "A"),
        ("stream_chain_beads", _f32(chain_beads), "B"),
        ("interstream_fork_bridges", _f32(fork_bridges), "A"),
        ("ocellus_teardrop_scales", _f32(teardrop_scales), "A"),
        ("cross_ocellus_rupture_slashes", _f32(rupture_slashes), "B"),
    )
    paint = np.broadcast_to(_rgb("#050410"), (S, S, 3)).copy()
    for mask, color, alpha in (
        (marks[0][1], "#1267ff", .94), (marks[1][1], "#25f5bd", .95),
        (marks[2][1], "#ff3ae0", .96), (marks[3][1], "#f7e52f", .93),
        (marks[4][1], "#ff7a19", .94), (marks[5][1], "#753dff", .92),
        (marks[6][1], "#2bd7ff", .92), (marks[7][1], "#ff3050", .95)):
        paint = _blend(paint, _rgb(color), alpha * mask)
    paint = _blend(paint, _rgb("#d7ff76"), .32 * tones["outer"] * marks[0][1])
    paint = _blend(paint, _rgb("#ffffff"), .30 * tones["bead"] * marks[4][1])

    # Peacock material: ring aperture, pupil metal and lash clearcoat are three
    # independent causal networks, unlike every other finish in this module.
    metal = _tier_write(12, (
        (tones["pupil"], (62, 90, 120, 150, 180, 208, 234, 255)),
        (tones["outer"], (34, 62, 92, 122, 154, 186, 220, 248)),
        (tones["tear"], (48, 76, 106, 136, 166, 196, 226, 252)),
    ))
    rough = _tier_write(230, (
        (tones["outer"], (210, 184, 158, 132, 106, 80, 52, 22)),
        (tones["inner"], (194, 168, 142, 116, 90, 64, 38, 12)),
        (tones["slash"], (220, 192, 164, 136, 108, 80, 50, 18)),
    ))
    coat = _tier_write(14, (
        (tones["lash"], (48, 78, 108, 138, 168, 198, 228, 254)),
        (tones["bead"], (76, 104, 132, 160, 188, 216, 240, 255)),
        (tones["bridge"], (36, 66, 98, 130, 162, 194, 226, 250)),
        (tones["inner"], (58, 88, 118, 148, 178, 208, 234, 252)),
    ))
    return _validate(Grammar(marks, _f32(paint),
                             _hue_null_from_marks(marks,
                                                   (.92, .56, .82, .70, .98, .44, .76, .64)),
                             (metal, rough, coat),
                             "vector-streamed asymmetric micro-ocelli with physical lashes and forks"))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fmo_sunset_moth": _build_sunset_moth,
    "fmo_atlas_wing": _build_atlas_wing,
    "fmo_glasswing": _build_glasswing,
    "fmo_peacock_eye": _build_peacock_eye,
}
HUES = {
    "fmo_sunset_moth": (.04, .48),
    "fmo_atlas_wing": (.10, .52),
    "fmo_glasswing": (.48, .84),
    "fmo_peacock_eye": (.60, .91),
}
MORPHO_FULLRES_IDS = tuple(BUILDERS)
ADVANCED_IDS: Tuple[str, ...] = ()
REJECTED_IDS = MORPHO_FULLRES_IDS
DEFERRED_IDS = MORPHO_FULLRES_IDS


@lru_cache(maxsize=4)
def _authored(fid: str) -> Tuple[np.ndarray, np.ndarray]:
    grammar = BUILDERS[fid]()
    spec = np.stack(grammar.explicit_spec, axis=2).astype(np.uint8)
    return grammar.paint, spec


def clear_cache() -> None:
    _authored.cache_clear()


def debug_grammar(fid: str) -> Grammar:
    return BUILDERS[fid]()


def debug_hue_null(fid: str) -> np.ndarray:
    return debug_grammar(fid).hue_null


def owner_unions(grammar: Grammar) -> Dict[str, np.ndarray]:
    unions = {key: np.zeros((S, S), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        unions[bank] = np.maximum(unions[bank], mask)
    return unions


def debug_angle_pair(fid: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Expose literal opposed A/B color flipping at authored resolution."""
    paint, spec = _authored(fid)
    owners = owner_unions(debug_grammar(fid))
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - .62 * rough, .18, 1.0)
    bank_a = np.clip(.12 + 1.08 * metal * aperture
                     + .56 * owners["A"] - .24 * owners["B"], .06, 1.36)
    bank_b = np.clip(.12 + 1.08 * coat * aperture
                     + .56 * owners["B"] - .24 * owners["A"], .06, 1.36)
    hue_a = np.asarray((.03, .20, .48), np.float32)
    hue_b = np.asarray((.42, .02, .29), np.float32)
    angle_a = np.clip(paint * bank_a[..., None]
                      + hue_a * (owners["A"] * aperture)[..., None], 0, 1)
    angle_b = np.clip(paint * bank_b[..., None]
                      + hue_b * (owners["B"] * aperture)[..., None], 0, 1)
    return (angle_a.astype(np.float32), angle_b.astype(np.float32),
            np.abs(angle_a - angle_b).astype(np.float32))


def render_native(fid: str, size: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
    paint, spec = _authored(fid)
    if size == S:
        return paint.copy(), spec.copy()
    paint_native = cv2.resize(paint, (size, size), interpolation=cv2.INTER_CUBIC)
    spec_native = cv2.resize(spec, (size, size), interpolation=cv2.INTER_NEAREST)
    return _f32(paint_native), spec_native.astype(np.uint8)


def _paint_dispatch(fid: str, paint, shape, mask, pm) -> np.ndarray:
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


def _spec_dispatch(fid: str, shape, mask, sm) -> np.ndarray:
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


# Isolated API contract.  These wrappers are not installed into production;
# final promotion must replace the helper dispatch with release-lock-compliant
# module-level owner logic if the owner accepts any candidate.
def _entry(fid: str):
    def spec_fn(shape, mask, seed, sm):
        return _spec_dispatch(fid, shape, mask, sm)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        return _paint_dispatch(fid, paint, shape, mask, pm)

    return spec_fn, paint_fn


def install_into_engine(registry, base_registry=None):
    # Full-resolution eye review rejected all four studies as repeated
    # micro-glyph/paver fields.  The isolated installer therefore exposes none.
    for fid in ADVANCED_IDS:
        registry[fid] = _entry(fid)
    return "fractured-wilds-fullres-morpho-batch: 0 advanced, 4 rejected"


__all__ = ["ADVANCED_IDS", "BUILDERS", "CALM_SPEC", "DEFERRED_IDS", "Grammar",
           "HUES", "MORPHO_FULLRES_IDS", "REJECTED_IDS",
           "_authored", "_entry", "clear_cache", "debug_angle_pair",
           "debug_grammar", "debug_hue_null", "install_into_engine",
           "owner_unions", "render_native"]
