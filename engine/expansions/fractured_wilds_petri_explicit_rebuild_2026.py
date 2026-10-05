# -*- coding: utf-8 -*-
"""Owner-eye rejection rebuild for the 20 FRACTURED PETRI finishes.

SPB-WILDS 2026-08-24, WR-PETRI-REJECTION-2. Owner verdict: Wilds committed
the app's "biggest cardinal sin PERIOD ... LAZY" by shipping recolored paint
and spec silhouettes; random noise is forbidden as a uniqueness device.

The first explicit Petri candidate still failed owner-eye review: fourteen
cards used shared row/grid/pave or sparse-stamp grammars, four required major
scale/topology repairs, and several spec channels contained unrelated macro
overlays. This file is the ground-up rejection correction. Each ID owns a
literal builder with at least seven causal biological marks, finish-local
metal/roughness/clearcoat ancestry, and explicit A/B Fractured material
ownership. There is no RNG, noise, grain, fleck layer, wrapped source tile,
generic topology router, or equal-population ranker.

Art is authored at 512 square. Lines, rims, pores, septa, beads, striae and
spines are 2-8 work pixels (8-32 native pixels at 2048). Larger identities
are connected assemblies of those fine primitives. Candidate only: never
describe this module as owner accepted without an actual owner review.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, Mapping, Sequence, Tuple

import cv2
import numpy as np

from engine.expansions.fractured_wilds_cryptid_rebuild_2026 import (
    _CALM_SPEC, _edge, _f32, _halo, _inside, _line, _local, _norm, _ring, _xy,
)


_WORK = 512
_TAU = np.float32(np.pi * 2.0)


@dataclass
class _Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    tone: np.ndarray
    metal: np.ndarray
    rough: np.ndarray
    coat: np.ndarray


def _new_marks(*names: str) -> Dict[str, np.ndarray]:
    return {name: np.zeros((_WORK, _WORK), np.float32) for name in names}


def _draw_line(mask: np.ndarray, a, b, value=1.0, width=2) -> None:
    cv2.line(mask, tuple(map(int, a)), tuple(map(int, b)), float(value),
             max(2, min(8, int(width))), cv2.LINE_AA)


def _draw_poly(mask: np.ndarray, pts, value=1.0, width=2, fill=False,
               closed=True) -> None:
    arr = np.asarray(pts, np.int32).reshape((-1, 1, 2))
    if fill:
        cv2.fillPoly(mask, [arr], float(value), cv2.LINE_AA)
    else:
        cv2.polylines(mask, [arr], bool(closed), float(value),
                      max(2, min(8, int(width))), cv2.LINE_AA)


def _disc(lx, ly, radius, feather=0.8):
    return _inside(np.hypot(lx, ly), radius, feather)


def _ellipse(lx, ly, rx, ry, feather=0.8):
    d = np.sqrt((np.asarray(lx) / float(rx)) ** 2 + (np.asarray(ly) / float(ry)) ** 2)
    return _inside(d, 1.0, float(feather) / max(float(rx), float(ry)))


def _ellipse_ring(lx, ly, rx, ry, width=0.10):
    d = np.sqrt((np.asarray(lx) / float(rx)) ** 2 + (np.asarray(ly) / float(ry)) ** 2)
    return _line(d - 1.0, float(width))


def _pack(masks: Mapping[str, np.ndarray], banks: Mapping[str, str], tone: np.ndarray,
          metal: np.ndarray, rough: np.ndarray, coat: np.ndarray) -> _Grammar:
    if len(masks) < 7:
        raise ValueError("lazy Petri grammar: fewer than seven causal marks")
    if set(masks) != set(banks):
        raise ValueError("every causal mark needs literal A/B/N ownership")
    owners = set(banks.values())
    if not {"A", "B"}.issubset(owners) or not owners.issubset({"A", "B", "N"}):
        raise ValueError("each Petri finish needs opposing A/B material features")
    marks = []
    for name, mask in masks.items():
        u = _f32(mask)
        if float(np.std(u)) < 0.002:
            raise ValueError(f"flat causal Petri mark {name!r}")
        marks.append((name, u, banks[name]))
    channels = tuple(_f32(field) for field in (metal, rough, coat))
    if any(float(np.std(field)) < 0.035 for field in channels):
        raise ValueError("flat finish-local Petri spec topology")
    return _Grammar(tuple(marks), _norm(tone), *channels)


def _hsv(h: float, s: float, v: float) -> np.ndarray:
    px = np.uint8([[[int((h % 1.0) * 179.0), int(np.clip(s, 0, 1) * 255),
                     int(np.clip(v, 0, 1) * 255)]]])
    return cv2.cvtColor(px, cv2.COLOR_HSV2RGB)[0, 0].astype(np.float32) / 255.0


_COLOR_BANDS = np.asarray([0.11, 0.25, 0.40, 0.56, 0.72, 0.87], np.float32)
_SPEC_BANDS = np.asarray([0.08, 0.17, 0.27, 0.38, 0.50, 0.63, 0.76], np.float32)


def _palette(hues: Sequence[float]):
    ha, hb = float(hues[0]), float(hues[1])
    offsets = (-0.070, -0.042, -0.018, 0.0, 0.025, 0.055, 0.092)
    values = (0.22, 0.31, 0.42, 0.55, 0.69, 0.83, 0.97)
    sat_a = (0.62, 0.72, 0.80, 0.88, 0.91, 0.82, 0.68)
    sat_b = (0.74, 0.86, 0.92, 0.84, 0.77, 0.70, 0.61)
    a = np.stack([_hsv(ha + offsets[i], sat_a[i], values[i]) for i in range(7)])
    b = np.stack([_hsv(hb - offsets[6 - i], sat_b[i], values[i]) for i in range(7)])
    neutral = np.stack([_hsv((ha + hb) * 0.5 + 0.50, 0.20, 0.13),
                        _hsv((ha + hb) * 0.5, 0.30, 0.52)])
    return a.astype(np.float32), b.astype(np.float32), neutral.astype(np.float32)


def _fixed_spec(field: np.ndarray, values: Sequence[int]) -> np.ndarray:
    return np.asarray(values, np.float32)[np.digitize(_f32(field), _SPEC_BANDS)]


def _compose(grammar: _Grammar, hues: Sequence[float]):
    bank_a, bank_b, neutral = _palette(hues)
    tone = grammar.tone
    paint = np.broadcast_to(neutral[0], (_WORK, _WORK, 3)).copy()
    for index, (_name, mask, owner) in enumerate(grammar.marks):
        if owner == "A":
            color = bank_a[np.digitize(np.mod(tone + index * 0.073, 1.0), _COLOR_BANDS)]
        elif owner == "B":
            color = bank_b[np.digitize(np.mod(1.0 - tone + (index + 2) * 0.073, 1.0),
                                       _COLOR_BANDS)]
        else:
            color = np.broadcast_to(neutral[(index + 1) & 1], paint.shape)
        alpha = np.clip(mask * (0.64 + 0.06 * (index % 5)), 0.0, 0.94)[..., None]
        paint = paint * (1.0 - alpha) + color * alpha

    # Spec response must stay attached to authored organisms.  The rejected
    # prototype let the smooth causal coordinate paint the entire background,
    # creating a generic macro contour overlay that visually overwhelmed the
    # biological marks.  Here A, B and neutral ownership provide three
    # different local supports; dilation is only a 2/5-pixel material falloff
    # from those literal marks, never an independent source pattern.
    zeros = np.zeros((_WORK, _WORK), np.float32)
    def owner_union(owner_name: str) -> np.ndarray:
        selected = [mask for _name, mask, owner in grammar.marks if owner == owner_name]
        return np.maximum.reduce(selected) if selected else zeros.copy()

    owner_a = owner_union("A")
    owner_b = owner_union("B")
    owner_n = owner_union("N")

    def local_support(primary: np.ndarray, secondary: np.ndarray,
                      tertiary: np.ndarray) -> np.ndarray:
        core = _f32(primary + 0.34 * secondary + 0.22 * tertiary)
        near = cv2.dilate(core, np.ones((5, 5), np.uint8))
        far = cv2.dilate(core, np.ones((11, 11), np.uint8))
        return _f32(np.maximum(core, np.maximum(0.62 * near, 0.27 * far)))

    metal_support = local_support(owner_a, owner_n, owner_b)
    rough_support = local_support(owner_n, owner_a, owner_b)
    coat_support = local_support(owner_b, owner_n, owner_a)
    metal_shade = np.mod(_norm(grammar.metal) * 0.83 + tone * 0.37, 1.0)
    rough_shade = np.mod(_norm(grammar.rough) * 0.79 + (1.0 - tone) * 0.43 + 0.19, 1.0)
    coat_shade = np.mod(_norm(grammar.coat) * 0.81 + np.sqrt(tone) * 0.41 + 0.37, 1.0)
    mf = 0.03 + metal_support * (0.18 + 0.79 * metal_shade)
    rf = 0.03 + rough_support * (0.18 + 0.79 * rough_shade)
    cf = 0.03 + coat_support * (0.18 + 0.79 * coat_shade)

    # Reserve all eight feature-local core shades (including the quiet tier).
    # This does not invent topology: every tier is painted only inside one of
    # this finish's literal causal marks.  Different permutations keep M/R/Cc
    # from collapsing to the same response even when two marks overlap.
    tier_centres = (0.03, 0.12, 0.22, 0.32, 0.44, 0.56, 0.69, 0.84)
    mark_masks = [mask for _name, mask, _owner in grammar.marks]

    def reserve_feature_tiers(field: np.ndarray, offset: int, stride: int) -> np.ndarray:
        out = field.copy()
        count = len(mark_masks)
        for tier, target in enumerate(tier_centres):
            mark = mark_masks[(offset + tier * stride) % count]
            out = np.where(mark > 0.78, np.float32(target), out)
        return out

    mf = reserve_feature_tiers(mf, 0, 1)
    rf = reserve_feature_tiers(rf, 1, 3)
    cf = reserve_feature_tiers(cf, 2, 5)
    metal = _fixed_spec(mf, (12, 42, 72, 104, 138, 172, 212, 246))
    rough = _fixed_spec(rf, (232, 52, 198, 78, 218, 106, 164, 34))
    coat = _fixed_spec(cf, (18, 188, 48, 226, 82, 156, 116, 244))
    return np.clip(paint, 0, 1).astype(np.float32), np.stack(
        [metal, rough, coat], axis=2).astype(np.uint8)


# Twenty explicit biological/material diagrams. Placement is authored by the
# named mechanism itself; no row/grid/pave compositor exists in this module.


def _build_fpe_magenta_bloom() -> _Grammar:
    """One asymmetric budding crown grows from a shared causal trunk."""
    names = ("mother_domes", "daughter_buds", "division_necks", "division_septa",
             "wet_rims", "contact_saddles", "rupture_scars", "satellite_cells")
    m = _new_marks(*names)
    frontier = [(np.asarray([256, 507], np.float32), -1.82),
                (np.asarray([256, 507], np.float32), -1.55),
                (np.asarray([256, 507], np.float32), -1.28)]
    lineage = 0
    for generation in range(7):
        next_frontier = []
        for start, angle in frontier:
            previous = start
            step_count = 6 + (lineage + generation) % 5
            for step in range(step_count):
                bend = angle + 0.13 * np.sin(step * 0.91 + lineage * 0.47)
                point = previous + np.asarray([np.cos(bend), np.sin(bend)]) * (
                    6.0 + (step + generation) % 3)
                if not (5 < point[0] < 507 and 5 < point[1] < 507):
                    break
                radius = 2 + (lineage + step + generation) % 4
                centre = tuple(np.rint(point).astype(int))
                cv2.circle(m["mother_domes"], centre, radius, 1.0, -1, cv2.LINE_AA)
                cv2.circle(m["wet_rims"], centre, radius + 2, 1.0, 2, cv2.LINE_AA)
                _draw_line(m["division_necks"], previous, point, 1.0, 2)
                normal = np.asarray([-np.sin(bend), np.cos(bend)], np.float32)
                _draw_line(m["division_septa"], point - normal * radius,
                           point + normal * radius, 1.0, 2)
                if (step + lineage) % 3 == 1:
                    side = -1 if (lineage + step) & 1 else 1
                    bud = point + normal * side * (radius + 5)
                    cv2.circle(m["daughter_buds"], tuple(np.rint(bud).astype(int)),
                               3, 1.0, -1, cv2.LINE_AA)
                    _draw_line(m["division_necks"], point, bud, 1.0, 2)
                if (step + generation) % 5 == 2:
                    cv2.circle(m["contact_saddles"], centre, 2, 1.0, -1, cv2.LINE_AA)
                if (step + lineage) % 7 == 4:
                    cv2.ellipse(m["rupture_scars"], centre, (radius + 1, radius),
                                np.degrees(bend), 190, 330, 1.0, 2, cv2.LINE_AA)
                if (step + generation * 2) % 6 == 0:
                    satellite = point - normal * (8 + lineage % 4)
                    cv2.circle(m["satellite_cells"],
                               tuple(np.rint(satellite).astype(int)), 2, 1.0, -1,
                               cv2.LINE_AA)
                previous = point
            if generation < 6 and 5 < previous[0] < 507 and 5 < previous[1] < 507:
                spread = 0.24 + generation * 0.035
                next_frontier.append((previous, angle - spread))
                if (lineage + generation) % 4 != 0:
                    next_frontier.append((previous, angle + spread * 0.91))
            lineage += 1
        frontier = next_frontier
    xg, yg = _xy()
    tone = _norm(np.sin(xg / 29.0) + np.cos(yg / 37.0) + (xg + yg) / 311.0)
    banks = dict(mother_domes="A", daughter_buds="B", division_necks="A",
                 division_septa="A", wet_rims="B", contact_saddles="N",
                 rupture_scars="N", satellite_cells="B")
    metal = _f32(0.06 + 0.62 * m["mother_domes"] + 0.53 * m["division_septa"]
                 + 0.42 * m["rupture_scars"] + 0.20 * tone)
    rough = _f32(0.10 + 0.60 * m["contact_saddles"] + 0.54 * m["rupture_scars"]
                 + 0.42 * m["division_necks"] + 0.21 * (1.0 - tone))
    coat = _f32(0.05 + 0.66 * m["daughter_buds"] + 0.58 * m["wet_rims"]
                + 0.47 * m["satellite_cells"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_cyan_membrane() -> _Grammar:
    """Broken double-leaflet lamellae sweep, fuse, bud and expose pore gates."""
    names = ("bilayer_walls", "leaflet_edges", "channel_gates", "vesicle_buds",
             "protein_rafts", "fusion_necks", "pore_rings", "broken_bilayer_ends",
             "transmembrane_proteins")
    m = _new_marks(*names)
    for patch in range(47):
        angle = -1.18 + patch * 0.413 + 0.31 * np.sin(patch * 0.77)
        cx = 256 + 236 * np.sin(patch * 1.731)
        cy = 256 + 232 * np.sin(patch * 2.117 + 0.61)
        tangent = np.asarray([np.cos(angle), np.sin(angle)])
        normal = np.asarray([-tangent[1], tangent[0]])
        centreline = []
        for step in range(-7, 8):
            base = np.asarray([cx, cy]) + tangent * step * 9.0
            base += normal * (5.0 * np.sin(step * 0.73 + patch))
            centreline.append(base)
        for side in (-1, 1):
            leaf = [p + normal * side * 3.2 for p in centreline]
            _draw_poly(m["bilayer_walls"], leaf, 1.0, 3, False, False)
            edge = [p + normal * side * 5.4 for p in centreline]
            _draw_poly(m["leaflet_edges"], edge, 1.0, 2, False, False)
        for step in (-5, -1, 3, 6):
            p = centreline[step + 7]
            _draw_line(m["transmembrane_proteins"], p - normal * 5.5,
                       p + normal * 5.5, 1.0, 2)
        mid = centreline[7]
        cv2.ellipse(m["channel_gates"], tuple(map(int, mid)), (5, 3),
                    np.degrees(angle), 0, 360, 1.0, 2, cv2.LINE_AA)
        bud = centreline[3] + normal * 8.0
        cv2.circle(m["vesicle_buds"], tuple(map(int, bud)), 5, 1.0, 2, cv2.LINE_AA)
        _draw_line(m["fusion_necks"], centreline[3], bud, 1.0, 3)
        pore = centreline[11] - normal * 7.0
        cv2.circle(m["pore_rings"], tuple(map(int, pore)), 3, 1.0, 2, cv2.LINE_AA)
        for p in centreline[2:13:3]:
            cv2.circle(m["protein_rafts"], tuple(map(int, p + normal * 2)), 2,
                       1.0, -1, cv2.LINE_AA)
        for p in (centreline[0], centreline[-1]):
            _draw_line(m["broken_bilayer_ends"], p - normal * 5, p + normal * 5,
                       1.0, 3)
    x, y = _xy()
    tone = _norm(np.sin((x + 0.4 * y) / 31.0) + np.cos((y - 0.3 * x) / 43.0))
    banks = dict(bilayer_walls="A", leaflet_edges="B", channel_gates="B",
                 vesicle_buds="A", protein_rafts="A", fusion_necks="N",
                 pore_rings="B", broken_bilayer_ends="N", transmembrane_proteins="A")
    metal = _f32(0.05 + 0.60 * m["protein_rafts"] + 0.56 * m["transmembrane_proteins"]
                 + 0.43 * m["bilayer_walls"] + 0.21 * tone)
    rough = _f32(0.10 + 0.62 * m["broken_bilayer_ends"] + 0.54 * m["pore_rings"]
                 + 0.41 * m["channel_gates"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.64 * m["leaflet_edges"] + 0.59 * m["vesicle_buds"]
                + 0.46 * m["fusion_necks"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_lime_culture() -> _Grammar:
    """Five hand-curved inoculation streaks bloom, collide and leave gaps."""
    names = ("clonal_cores", "young_growth_fronts", "mutation_sectors",
             "sector_boundaries", "nutrient_channels", "division_septa",
             "satellite_colonies", "inhibition_gaps")
    m = _new_marks(*names)
    streaks = (
        ((12, 62), (167, 5), (492, 94), (116, 238)),
        ((24, 454), (166, 260), (489, 503), (497, 191)),
        ((486, 31), (322, 87), (48, 291), (392, 354)),
        ((42, 289), (240, 492), (353, 26), (487, 476)),
        ((9, 177), (177, 386), (382, 144), (506, 327)),
    )
    for streak_index, controls in enumerate(streaks):
        p0, p1, p2, p3 = (np.asarray(point, np.float32) for point in controls)
        previous = None
        for sample in range(91):
            t = sample / 90.0
            omt = 1.0 - t
            point = (omt ** 3 * p0 + 3.0 * omt * omt * t * p1
                     + 3.0 * omt * t * t * p2 + t ** 3 * p3)
            derivative = (3.0 * omt * omt * (p1 - p0)
                          + 6.0 * omt * t * (p2 - p1)
                          + 3.0 * t * t * (p3 - p2))
            tangent = derivative / max(1.0, float(np.linalg.norm(derivative)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            # Three inoculum passes diverge and rejoin rather than forming
            # parallel rows; their separation is phase-modulated and local.
            pass_indices = (-1, 0, 1) if streak_index in (0, 3) else (
                (-1, 1) if streak_index in (1, 4) else (0,))
            for pass_index in pass_indices:
                offset = pass_index * (6.0 + 3.0 * np.sin(sample * 0.19
                                                         + streak_index * 1.3))
                centre = point + normal * offset
                if not (5 < centre[0] < 507 and 5 < centre[1] < 507):
                    continue
                if (sample + streak_index * 7 + pass_index * 3) % 17 in (0, 1):
                    cv2.ellipse(m["inhibition_gaps"], tuple(np.rint(centre).astype(int)),
                                (6, 3), float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                                185, 344, 1.0, 2, cv2.LINE_AA)
                    continue
                size = 2 + ((sample + streak_index + pass_index) % 3)
                c = tuple(np.rint(centre).astype(int))
                cv2.circle(m["clonal_cores"], c, 2, 1.0, -1, cv2.LINE_AA)
                cv2.circle(m["young_growth_fronts"], c, size + 2, 1.0, 2, cv2.LINE_AA)
                sector_angle = float(np.degrees(np.arctan2(tangent[1], tangent[0])))
                cv2.ellipse(m["mutation_sectors"], c, (size + 1, size + 1),
                            sector_angle, 18, 104, 1.0, 2, cv2.LINE_AA)
                _draw_line(m["sector_boundaries"], centre,
                           centre + normal * (size + 2), 1.0, 2)
                _draw_line(m["division_septa"], centre - tangent * 2,
                           centre + tangent * 2, 1.0, 2)
                if (sample + pass_index) % 8 == 3:
                    satellite = centre + normal * (9 + (sample % 5))
                    cv2.circle(m["satellite_colonies"],
                               tuple(np.rint(satellite).astype(int)), 2, 1.0, -1,
                               cv2.LINE_AA)
            if previous is not None and sample % 17 not in (0, 1):
                _draw_line(m["nutrient_channels"], previous, point, 1.0, 2)
            previous = point
    x, y = _xy()
    tone = _norm(np.sin((x + y) / 43.0) + np.cos((x - 2.0 * y) / 67.0))
    banks = dict(clonal_cores="A", young_growth_fronts="B", mutation_sectors="A",
                 sector_boundaries="N", nutrient_channels="B", division_septa="A",
                 satellite_colonies="B", inhibition_gaps="N")
    metal = _f32(0.05 + 0.61 * m["clonal_cores"] + 0.55 * m["mutation_sectors"]
                 + 0.44 * m["division_septa"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["inhibition_gaps"] + 0.51 * m["sector_boundaries"]
                 + 0.40 * m["nutrient_channels"] + 0.21 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["young_growth_fronts"] + 0.58 * m["satellite_colonies"]
                + 0.43 * m["nutrient_channels"] + 0.18 * (1.0 - tone))
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_amber_agar() -> _Grammar:
    """Branching dehydration fractures subdivide agar into irregular wet plates."""
    names = ("dry_agar_plates", "primary_cracks", "secondary_crazing",
             "lifted_crack_lips", "moist_islands", "healed_bridges",
             "junction_pits", "plate_crazing")
    m = _new_marks(*names)
    impacts = ((-8, 87), (126, -6), (294, 39), (520, 117),
               (451, 294), (339, 518), (147, 476), (19, 347), (245, 248))
    for impact_index, (cx, cy) in enumerate(impacts):
        ray_count = 5 + impact_index % 4
        for ray in range(ray_count):
            angle = impact_index * 0.91 + ray * _TAU / ray_count
            previous = (cx, cy)
            for step in range(1, 23):
                bend = angle + 0.13 * np.sin(step * 0.67 + ray * 1.7 + impact_index)
                length = step * (5.5 + 0.35 * ((ray + step) % 4))
                point = (cx + np.cos(bend) * length, cy + np.sin(bend) * length)
                if not (2 <= point[0] < 510 and 2 <= point[1] < 510):
                    break
                _draw_line(m["primary_cracks"], previous, point, 1.0, 3)
                if step % 3 == 1:
                    side = bend + (-1 if step & 1 else 1) * 0.86
                    branch = (point[0] + np.cos(side) * 13, point[1] + np.sin(side) * 13)
                    _draw_line(m["secondary_crazing"], point, branch, 1.0, 2)
                    lip_a = np.asarray(point) + np.asarray([-np.sin(bend), np.cos(bend)]) * 3
                    lip_b = np.asarray(branch) + np.asarray([-np.sin(bend), np.cos(bend)]) * 3
                    _draw_line(m["lifted_crack_lips"], lip_a, lip_b, 1.0, 2)
                    if step % 6 == 1:
                        tip = np.asarray(branch)
                        cv2.ellipse(m["moist_islands"], tuple(np.rint(tip).astype(int)),
                                    (4 + ray % 3, 2 + impact_index % 3),
                                    float(np.degrees(side)), 0, 360, 1.0, 2,
                                    cv2.LINE_AA)
                    tertiary = np.asarray(branch) + np.asarray(
                        [np.cos(side + 0.74), np.sin(side + 0.74)]) * 7
                    _draw_line(m["plate_crazing"], branch, tertiary, 1.0, 2)
                if step % 4 == 2:
                    cv2.circle(m["junction_pits"], tuple(map(int, point)), 2, 1.0, -1, cv2.LINE_AA)
                if step % 7 == 4:
                    normal = np.asarray([-np.sin(bend), np.cos(bend)])
                    _draw_line(m["healed_bridges"], np.asarray(point) - normal * 4,
                               np.asarray(point) + normal * 4, 1.0, 3)
                if step % 5 == 3:
                    normal = np.asarray([-np.sin(bend), np.cos(bend)])
                    plate = (np.asarray(point) + normal * 6,
                             np.asarray(point) + normal * 10 +
                             np.asarray([np.cos(bend), np.sin(bend)]) * 4,
                             np.asarray(point) + normal * 6 +
                             np.asarray([np.cos(bend), np.sin(bend)]) * 8,
                             np.asarray(point) + normal * 3 +
                             np.asarray([np.cos(bend), np.sin(bend)]) * 4)
                    _draw_poly(m["dry_agar_plates"], plate, 1.0, 2, False, True)
                previous = point
    crack_union = np.maximum(m["primary_cracks"], m["secondary_crazing"])
    distance = cv2.distanceTransform((crack_union < 0.1).astype(np.uint8), cv2.DIST_L2, 3)
    x, y = _xy()
    tone = _norm(np.minimum(distance, 19.0) + np.sin(x / 31.0) + np.cos(y / 43.0))
    banks = dict(dry_agar_plates="A", primary_cracks="A", secondary_crazing="B",
                 lifted_crack_lips="B", moist_islands="B", healed_bridges="A",
                 junction_pits="N", plate_crazing="N")
    metal = _f32(0.05 + 0.60 * m["healed_bridges"] + 0.54 * m["plate_crazing"]
                 + 0.42 * m["dry_agar_plates"] + 0.20 * tone)
    rough = _f32(0.10 + 0.64 * m["primary_cracks"] + 0.56 * m["secondary_crazing"]
                 + 0.45 * m["junction_pits"] + 0.20 * distance / 24.0)
    coat = _f32(0.05 + 0.65 * m["moist_islands"] + 0.59 * m["lifted_crack_lips"]
                + 0.43 * m["healed_bridges"] + 0.18 * (1.0 - tone))
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_violet_garden() -> _Grammar:
    """One rooted willow canopy hangs, forks, heals and fruits."""
    names = ("branch_trunks", "side_branches", "active_tips", "trapped_voids",
             "age_bands", "spore_bulbs", "anastomosis_bridges", "dead_end_scars")
    m = _new_marks(*names)
    # The crown is one organism, not a stack of interchangeable rails.  Two
    # root bundles twist into one arch; every pendant inherits a distinct
    # point and tangent on that arch.
    arch = []
    for sample in range(241):
        t = sample / 240.0
        x = 28.0 + 458.0 * t + 12.0 * np.sin(5.0 * np.pi * t)
        y = (326.0 - 235.0 * np.sin(np.pi * t)
             + 28.0 * np.sin(3.0 * np.pi * t + 0.37))
        arch.append(np.asarray([x, y], np.float32))
    _draw_poly(m["branch_trunks"], arch, 1.0, 4, False, False)
    root_controls = (
        ((244, 511), (216, 424), (101, 379), arch[30]),
        ((267, 511), (286, 409), (421, 372), arch[206]),
        ((254, 509), (252, 395), (235, 289), arch[119]),
    )
    for root_index, controls in enumerate(root_controls):
        p0, p1, p2, p3 = (np.asarray(point, np.float32) for point in controls)
        root = []
        for sample in range(65):
            t = sample / 64.0
            omt = 1.0 - t
            root.append(omt ** 3 * p0 + 3 * omt * omt * t * p1
                        + 3 * omt * t * t * p2 + t ** 3 * p3)
        _draw_poly(m["branch_trunks"], root, 1.0, 3, False, False)
        for sample in range(9 + root_index, 61, 7 + root_index):
            tangent = root[min(64, sample + 2)] - root[max(0, sample - 2)]
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            side = -1 if (sample // 7 + root_index) & 1 else 1
            start = root[sample]
            fork = start + normal * side * (9 + (sample * 3) % 17)
            fork += tangent * (((sample + root_index) % 5) - 2) * 3
            _draw_line(m["side_branches"], start, fork, 1.0, 2)
            cv2.circle(m["active_tips"], tuple(np.rint(fork).astype(int)),
                       2, 1.0, -1, cv2.LINE_AA)
            if sample % 3:
                cv2.ellipse(m["spore_bulbs"], tuple(np.rint(fork).astype(int)),
                            (3 + sample % 3, 2 + root_index), sample * 11,
                            0, 360, 1.0, 2, cv2.LINE_AA)
            _draw_line(m["age_bands"], start - normal * 3,
                       start + normal * 3, 1.0, 2)

    pendant_ends = []
    anchors = tuple(range(5, 239, 5))
    for index, anchor_index in enumerate(anchors):
        origin = arch[anchor_index]
        tangent = arch[min(240, anchor_index + 2)] - arch[max(0, anchor_index - 2)]
        tangent /= max(1.0, float(np.linalg.norm(tangent)))
        length = 35.0 + ((index * 37) % 143)
        sway = ((index * 19) % 33) - 16
        points = [origin]
        for step in range(1, 13):
            u = step / 12.0
            point = origin + np.asarray([
                sway * np.sin(np.pi * u) + 9.0 * np.sin(step * 0.71 + index),
                length * u + 7.0 * np.sin(step * 0.53 + index * 0.83),
            ], np.float32)
            point = np.clip(point, 5, 507)
            points.append(point)
        _draw_poly(m["side_branches"], points, 1.0, 2 + index % 2, False, False)
        end = points[-1]
        pendant_ends.append(end)
        cv2.circle(m["active_tips"], tuple(np.rint(end).astype(int)),
                   2 + index % 2, 1.0, -1, cv2.LINE_AA)
        if index % 3 != 1:
            cv2.ellipse(m["spore_bulbs"], tuple(np.rint(end).astype(int)),
                        (3 + index % 3, 2 + (index + 1) % 3), index * 19,
                        0, 360, 1.0, 2, cv2.LINE_AA)
        for step in (3 + index % 2, 7 + index % 3):
            local = points[min(11, step + 1)] - points[max(0, step - 1)]
            local /= max(1.0, float(np.linalg.norm(local)))
            normal = np.asarray([-local[1], local[0]], np.float32)
            _draw_line(m["age_bands"], points[step] - normal * 3,
                       points[step] + normal * 3, 1.0, 2)
        fork_step = 5 + index % 4
        fork_angle = (-0.91 if index & 1 else 0.74)
        fork = points[fork_step] + np.asarray([np.cos(fork_angle),
                                               np.sin(fork_angle)]) * (11 + index % 7)
        _draw_line(m["side_branches"], points[fork_step], fork, 1.0, 2)
        second_step = 8 + index % 3
        second_angle = 0.43 if index % 3 else -0.58
        second_fork = points[second_step] + np.asarray(
            [np.cos(second_angle), np.sin(second_angle)]) * (8 + index % 6)
        _draw_line(m["side_branches"], points[second_step], second_fork, 1.0, 2)
        if index % 2 == 0:
            cv2.circle(m["active_tips"], tuple(np.rint(second_fork).astype(int)),
                       2, 1.0, -1, cv2.LINE_AA)
        cv2.ellipse(m["trapped_voids"], tuple(np.rint(points[fork_step]).astype(int)),
                    (4 + index % 3, 2 + (index + 1) % 2), index * 23,
                    0, 295, 1.0, 2, cv2.LINE_AA)
        if index % 4 == 2:
            cv2.circle(m["dead_end_scars"], tuple(np.rint(fork).astype(int)),
                       3, 1.0, 2, cv2.LINE_AA)
    for left, right in ((2, 4), (6, 9), (11, 14), (16, 19), (21, 24),
                        (27, 30), (32, 35), (37, 40), (42, 45)):
        a, b = pendant_ends[left], pendant_ends[right]
        bridge_mid = (a + b) * 0.5 + np.asarray([0, -9 - left % 5], np.float32)
        _draw_poly(m["anastomosis_bridges"], (a, bridge_mid, b),
                   1.0, 2, False, False)
    x, y = _xy()
    tone = _norm((512.0 - y) / 512.0 + np.sin(x / 41.0) + np.cos((x + y) / 57.0))
    banks = dict(branch_trunks="A", side_branches="A", active_tips="B",
                 trapped_voids="N", age_bands="N", spore_bulbs="B",
                 anastomosis_bridges="B", dead_end_scars="N")
    metal = _f32(0.05 + 0.61 * m["branch_trunks"] + 0.53 * m["age_bands"]
                 + 0.43 * m["side_branches"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["trapped_voids"] + 0.55 * m["dead_end_scars"]
                 + 0.41 * m["age_bands"] + 0.19 * (1.0 - tone))
    coat = _f32(0.05 + 0.66 * m["active_tips"] + 0.59 * m["spore_bulbs"]
                + 0.45 * m["anastomosis_bridges"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_lime_diatom() -> _Grammar:
    """A valve school turns through three colliding eddies without carriers."""
    names = ("boat_valves", "silica_rims", "raphe_slits", "bilateral_striae",
             "costae_ribs", "central_nodules", "terminal_pores", "girdle_bands",
             "broken_valve_chips")
    m = _new_marks(*names)
    def draw_valve(point: np.ndarray, direction: np.ndarray, index: int) -> None:
        if not (12 < point[0] < 500 and 10 < point[1] < 502):
            return
        tangent = direction / max(1.0e-4, float(np.linalg.norm(direction)))
        angle = float(np.degrees(np.arctan2(tangent[1], tangent[0])))
        angle += ((index % 5) - 2) * 6
        tangent = np.asarray([np.cos(np.deg2rad(angle)),
                              np.sin(np.deg2rad(angle))])
        normal = np.asarray([-tangent[1], tangent[0]])
        length = 6 + index % 6
        width = 3 + (index // 2) % 3
        centre = tuple(np.rint(point).astype(int))
        archetype = index % 8
        if archetype == 0:
            cv2.ellipse(m["boat_valves"], centre, (length, width), angle,
                        0, 360, 1.0, -1, cv2.LINE_AA)
            cv2.ellipse(m["silica_rims"], centre, (length + 1, width + 1), angle,
                        0, 360, 1.0, 2, cv2.LINE_AA)
        elif archetype == 1:
            hull = (point + tangent * length,
                    point + normal * width,
                    point - tangent * length,
                    point - normal * width)
            _draw_poly(m["boat_valves"], hull, 1.0, 2, False, True)
            rim = [point + (np.asarray(vertex) - point) * 1.18 for vertex in hull]
            _draw_poly(m["silica_rims"], rim, 1.0, 2, False, True)
        elif archetype == 2:
            bend = point + normal * (2 + index % 3)
            _draw_poly(m["boat_valves"],
                       (point - tangent * length, bend, point + tangent * length),
                       1.0, 3, False, False)
            _draw_poly(m["silica_rims"],
                       (point - tangent * length - normal * 2,
                        bend - normal * 2,
                        point + tangent * length - normal * 2),
                       1.0, 2, False, False)
        elif archetype == 3:
            cv2.ellipse(m["boat_valves"], centre, (length, width + 1), angle,
                        28, 327, 1.0, 3, cv2.LINE_AA)
            cv2.ellipse(m["silica_rims"], centre, (length + 2, width + 2), angle,
                        186, 349, 1.0, 2, cv2.LINE_AA)
        elif archetype == 4:
            for sign in (-1, 1):
                lobe = point + tangent * sign * max(3, length - 3)
                cv2.circle(m["boat_valves"], tuple(np.rint(lobe).astype(int)),
                           max(2, width - 1), 1.0, -1, cv2.LINE_AA)
                cv2.circle(m["silica_rims"], tuple(np.rint(lobe).astype(int)),
                           width + 1, 1.0, 2, cv2.LINE_AA)
            _draw_line(m["boat_valves"], point - tangent * (length - 4),
                       point + tangent * (length - 4), 1.0, 2)
        elif archetype == 5:
            wedge = (point + tangent * length,
                     point - tangent * (length - 2) + normal * width,
                     point - tangent * (length - 2) - normal * width)
            _draw_poly(m["boat_valves"], wedge, 1.0, 2, False, True)
            rim = [point + (np.asarray(vertex) - point) * 1.18 for vertex in wedge]
            _draw_poly(m["silica_rims"], rim, 1.0, 2, False, True)
        elif archetype == 6:
            s_points = (point - tangent * length - normal * 2,
                        point - tangent * (length * 0.33) + normal * 3,
                        point + tangent * (length * 0.33) - normal * 3,
                        point + tangent * length + normal * 2)
            _draw_poly(m["boat_valves"], s_points, 1.0, 3, False, False)
            _draw_poly(m["silica_rims"],
                       tuple(np.asarray(p) + normal * 2 for p in s_points),
                       1.0, 2, False, False)
        else:
            cv2.ellipse(m["boat_valves"], centre, (length, width + 2), angle,
                        12, 151, 1.0, 3, cv2.LINE_AA)
            cv2.ellipse(m["silica_rims"], centre, (length, width + 2), angle,
                        197, 336, 1.0, 3, cv2.LINE_AA)
        if archetype in (0, 2, 6):
            _draw_line(m["raphe_slits"], point - tangent * (length - 2),
                       point + tangent * (length - 2), 1.0, 2)
        if archetype in (0, 3, 5, 7):
            bands = (-0.55, 0.0, 0.55) if archetype in (0, 3) else (-0.42, 0.42)
            for band in bands:
                p = point + tangent * length * band
                _draw_line(m["bilateral_striae"], p - normal * width,
                           p + normal * width, 1.0, 2)
        if archetype in (1, 4, 5, 7):
            _draw_line(m["costae_ribs"], point - normal * width,
                       point + normal * width, 1.0, 2)
        if archetype in (0, 1, 4, 6):
            cv2.circle(m["central_nodules"], centre, 2, 1.0, -1, cv2.LINE_AA)
        if archetype in (0, 2, 5, 7):
            for sign in (-1, 1):
                pore = point + tangent * (length - 1) * sign
                cv2.circle(m["terminal_pores"], tuple(np.rint(pore).astype(int)),
                           2, 1.0, 2, cv2.LINE_AA)
        if index % 7 == 0:
            cv2.ellipse(m["broken_valve_chips"], centre, (length + 2, width + 2),
                        angle, 20, 85, 1.0, 2, cv2.LINE_AA)
        if index % 4 == 1:
            cv2.ellipse(m["girdle_bands"], centre, (length - 2, width + 2), angle,
                        170, 350, 1.0, 2, cv2.LINE_AA)

    vortices = ((128.0, 151.0, 2.3), (371.0, 188.0, -2.0),
                (264.0, 383.0, 2.6))

    def flow(point: np.ndarray) -> np.ndarray:
        px, py = float(point[0]), float(point[1])
        vector = np.asarray([0.54 + 0.18 * np.cos(py / 57.0),
                             -0.13 + 0.17 * np.sin(px / 61.0)], np.float32)
        for cx, cy, circulation in vortices:
            dx, dy = px - cx, py - cy
            influence = circulation * 460.0 / (dx * dx + dy * dy + 310.0)
            vector += np.asarray([-dy, dx], np.float32) * influence
        return vector / max(0.25, float(np.linalg.norm(vector)))

    valve_index = 0
    golden = np.pi * (3.0 - np.sqrt(5.0))
    for eddy_index, (cx, cy, circulation) in enumerate(vortices):
        for index in range(146):
            u = (index + 0.61) / 146.0
            theta = index * golden + eddy_index * 1.17
            if eddy_index == 0:
                radius = 14.0 + 151.0 * np.sqrt(u)
                point = np.asarray([
                    cx + radius * np.cos(theta) * (1.0 + 0.13 * np.sin(3.0 * theta)),
                    cy + radius * np.sin(theta) * 0.70,
                ], np.float32)
            elif eddy_index == 1:
                p0 = np.asarray([206, 64], np.float32)
                p1 = np.asarray([302, 18], np.float32)
                p2 = np.asarray([426, 325], np.float32)
                p3 = np.asarray([502, 214], np.float32)
                omt = 1.0 - u
                axis = (omt ** 3 * p0 + 3.0 * omt * omt * u * p1
                        + 3.0 * omt * u * u * p2 + u ** 3 * p3)
                derivative = (3.0 * omt * omt * (p1 - p0)
                              + 6.0 * omt * u * (p2 - p1)
                              + 3.0 * u * u * (p3 - p2))
                derivative /= max(1.0, float(np.linalg.norm(derivative)))
                cross = np.asarray([-derivative[1], derivative[0]], np.float32)
                width = 19.0 + 67.0 * np.sin(np.pi * u) ** 0.7
                point = axis + cross * np.sin(theta) * width
                point += derivative * np.cos(theta * 0.63) * 13.0
            else:
                root = np.sqrt(u)
                across = np.mod(index * 0.61803398875 + 0.17, 1.0)
                a = np.asarray([38, 486], np.float32)
                b = np.asarray([207, 281], np.float32)
                c = np.asarray([451, 467], np.float32)
                point = ((1.0 - root) * a + root * (1.0 - across) * b
                         + root * across * c)
                point += np.asarray([11.0 * np.sin(theta * 0.81),
                                     9.0 * np.cos(theta * 1.17)], np.float32)
            if not (11 < point[0] < 501 and 11 < point[1] < 501):
                continue
            direction = flow(point)
            if circulation < 0:
                direction *= -1.0
            draw_valve(point, direction, valve_index)
            valve_index += 1
    x, y = _xy()
    tone = _norm(x / 512.0 + np.sin(y / 37.0) + np.cos((x + y) / 53.0))
    banks = dict(boat_valves="A", silica_rims="B", raphe_slits="N",
                 bilateral_striae="B", costae_ribs="A", central_nodules="A",
                 terminal_pores="B", girdle_bands="B", broken_valve_chips="N")
    metal = _f32(0.05 + 0.61 * m["boat_valves"] + 0.54 * m["costae_ribs"]
                 + 0.45 * m["central_nodules"] + 0.20 * tone)
    rough = _f32(0.10 + 0.62 * m["raphe_slits"] + 0.56 * m["broken_valve_chips"]
                 + 0.41 * m["bilateral_striae"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.66 * m["silica_rims"] + 0.58 * m["girdle_bands"]
                + 0.46 * m["terminal_pores"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_magenta_mosaic() -> _Grammar:
    """Interlocking epithelial fingers close one three-armed wound."""
    names = ("tissue_plates", "cell_membranes", "nuclei", "chromatin_bodies",
             "division_furrows", "junction_nodes", "torn_cell_edges", "tissue_bridges")
    m = _new_marks(*names)
    junction = np.asarray([264, 264], np.float32)
    arms = (
        ((264, 264), (198, 204), (111, 98), (18, 31)),
        ((264, 264), (337, 207), (417, 83), (502, 72)),
        ((264, 264), (242, 341), (328, 432), (351, 506)),
    )
    cell_index = 0
    arm_points = []
    for arm_index, controls in enumerate(arms):
        p0, p1, p2, p3 = (np.asarray(point, np.float32) for point in controls)
        points = []
        for sample in range(97):
            t = sample / 96.0
            omt = 1.0 - t
            point = (omt ** 3 * p0 + 3 * omt * omt * t * p1
                     + 3 * omt * t * t * p2 + t ** 3 * p3)
            point += np.asarray([6.0 * np.sin(sample * 0.41 + arm_index),
                                 5.0 * np.sin(sample * 0.63 + arm_index * 1.7)])
            points.append(point)
        arm_points.append(points)
        _draw_poly(m["torn_cell_edges"], points, 1.0, 4, False, False)
        for sample in range(4, 93, 3 + arm_index):
            centreline = points[sample]
            tangent = points[sample + 2] - points[sample - 2]
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            for side in (-1, 1):
                # Unequal interlocking fingers hug a single laceration; there
                # is no rectangular carrier and no repeated nine-lane pave.
                reach = 8.0 + ((sample * 7 + arm_index * 11 + side * 3) % 17)
                centre = centreline + normal * side * reach
                centre += tangent * (((sample + side * arm_index) % 7) - 3)
                radius = 4 + (sample + arm_index + side) % 5
                sides = 4 + (cell_index + arm_index) % 4
                phase = sample * 0.29 + arm_index * 0.77 + side * 0.31
                poly = []
                for vertex in range(sides):
                    angle = phase + vertex * _TAU / sides
                    stretch = 0.74 + 0.28 * (1 + np.sin(vertex * 1.91 + sample))
                    poly.append(centre + np.asarray([np.cos(angle), np.sin(angle)])
                                * radius * stretch)
                _draw_poly(m["cell_membranes"], poly, 1.0, 2, False, True)
                inset = [centre + (np.asarray(point) - centre) * 0.57 for point in poly]
                _draw_poly(m["tissue_plates"], inset, 1.0, 2, False, True)
                nucleus = centre + tangent * (((sample + side) % 5) - 2) * 0.8
                nc = tuple(np.rint(nucleus).astype(int))
                cv2.ellipse(m["nuclei"], nc, (3 + cell_index % 2, 2),
                            float(np.degrees(phase)), 0, 360, 1.0, 2, cv2.LINE_AA)
                cv2.circle(m["chromatin_bodies"], nc, 2, 1.0, -1, cv2.LINE_AA)
                if cell_index % 5 == 0:
                    _draw_line(m["division_furrows"], centre - tangent * radius,
                               centre + tangent * radius, 1.0, 2)
                if cell_index % 4 == 1:
                    cv2.circle(m["junction_nodes"], tuple(np.rint(poly[0]).astype(int)),
                               2, 1.0, -1, cv2.LINE_AA)
                cell_index += 1
            if (sample + arm_index) % 11 in (1, 5):
                bridge = 6 + (sample % 5)
                _draw_line(m["tissue_bridges"], centreline - normal * bridge,
                           centreline + normal * bridge, 1.0, 3)
    # Broad healing islands grow causally away from selected wound margins.
    # Branching ancestry breaks the earlier single-file necklace reading.
    island_samples = (13, 31, 52, 74, 89)
    lineage = 0
    for arm_index, points in enumerate(arm_points):
        for seed_index, sample in enumerate(island_samples):
            tangent = points[min(96, sample + 2)] - points[max(0, sample - 2)]
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            for side in (-1, 1):
                start = points[sample] + normal * side * (17 + seed_index * 2)
                base_angle = float(np.arctan2(normal[1] * side,
                                              normal[0] * side))
                frontier = [(start, base_angle)]
                for generation in range(4):
                    next_frontier = []
                    for branch_index, (parent, angle) in enumerate(frontier):
                        bend = angle + 0.33 * np.sin(lineage * 0.71
                                                     + generation * 1.13)
                        centre = parent + np.asarray([np.cos(bend), np.sin(bend)]) * (
                            9 + (lineage + generation) % 7)
                        if not (7 < centre[0] < 505 and 7 < centre[1] < 505):
                            continue
                        radius = 4 + (lineage + generation) % 5
                        sides = 4 + (lineage + arm_index) % 4
                        phase = bend + lineage * 0.19
                        poly = []
                        for vertex in range(sides):
                            angle_v = phase + vertex * _TAU / sides
                            stretch = 0.78 + 0.29 * (1.0 + np.sin(
                                vertex * 1.73 + lineage * 0.37))
                            poly.append(centre + np.asarray(
                                [np.cos(angle_v), np.sin(angle_v)]) * radius * stretch)
                        _draw_poly(m["cell_membranes"], poly, 1.0, 2, False, True)
                        inset = [centre + (np.asarray(point) - centre) * 0.55
                                 for point in poly]
                        _draw_poly(m["tissue_plates"], inset, 1.0, 2, False, True)
                        _draw_line(m["tissue_bridges"], parent, centre, 1.0, 2)
                        nc = tuple(np.rint(centre).astype(int))
                        cv2.ellipse(m["nuclei"], nc, (3, 2), np.degrees(bend),
                                    0, 360, 1.0, 2, cv2.LINE_AA)
                        cv2.circle(m["chromatin_bodies"], nc, 2, 1.0,
                                   -1, cv2.LINE_AA)
                        if lineage % 4 == 0:
                            branch_normal = np.asarray([-np.sin(bend),
                                                        np.cos(bend)], np.float32)
                            _draw_line(m["division_furrows"],
                                       centre - branch_normal * radius,
                                       centre + branch_normal * radius, 1.0, 2)
                        if lineage % 5 == 2:
                            cv2.circle(m["junction_nodes"],
                                       tuple(np.rint(poly[0]).astype(int)),
                                       2, 1.0, -1, cv2.LINE_AA)
                        if generation < 3:
                            spread = 0.39 + 0.04 * generation
                            next_frontier.append((centre, bend - spread))
                            if (lineage + generation) % 3:
                                next_frontier.append((centre, bend + spread * 0.87))
                        lineage += 1
                    frontier = next_frontier
    cv2.circle(m["junction_nodes"], tuple(np.rint(junction).astype(int)),
               6, 1.0, 2, cv2.LINE_AA)
    for points in arm_points:
        _draw_line(m["tissue_bridges"], junction, points[8], 1.0, 3)
    x, y = _xy()
    tone = _norm(np.sin(x / 47.0) + np.cos(y / 39.0) + (x - y) / 417.0)
    banks = dict(tissue_plates="A", cell_membranes="B", nuclei="A",
                 chromatin_bodies="A", division_furrows="N", junction_nodes="B",
                 torn_cell_edges="N", tissue_bridges="B")
    metal = _f32(0.05 + 0.61 * m["nuclei"] + 0.55 * m["chromatin_bodies"]
                 + 0.43 * m["tissue_plates"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["torn_cell_edges"] + 0.54 * m["division_furrows"]
                 + 0.42 * m["tissue_plates"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["cell_membranes"] + 0.58 * m["junction_nodes"]
                + 0.45 * m["tissue_bridges"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_cyan_spineball() -> _Grammar:
    """One shattered geodesic cage opens into a ruptured spine crown."""
    names = ("shell_cages", "polygon_pores", "radial_struts", "inner_cages",
             "spine_roots", "tapered_spines", "broken_sockets", "aperture_collars")
    m = _new_marks(*names)
    centre = np.asarray([251.0, 262.0], np.float32)
    golden = np.pi * (3.0 - np.sqrt(5.0))
    nodes = []
    for index in range(173):
        radius = np.sqrt((index + 0.72) / 173.0)
        theta = index * golden + 0.23
        # The right-side fracture removes one wedge from a single projected
        # cage.  These are mesh vertices, never repeated micro-spheres.
        if -0.42 < np.arctan2(np.sin(theta), np.cos(theta)) < 0.34 and radius > 0.48:
            continue
        warp = 1.0 + 0.08 * np.sin(3.0 * theta) + 0.05 * np.sin(7.0 * theta)
        point = centre + np.asarray([205.0 * radius * warp * np.cos(theta),
                                     174.0 * radius * (2.0 - warp) * np.sin(theta)],
                                    np.float32)
        if 9 < point[0] < 503 and 9 < point[1] < 503:
            nodes.append(point)
    subdiv = cv2.Subdiv2D((0, 0, _WORK, _WORK))
    for point in nodes:
        subdiv.insert((float(point[0]), float(point[1])))
    triangles = subdiv.getTriangleList()
    tri_index = 0
    for triangle in triangles:
        points = [np.asarray(triangle[0:2], np.float32),
                  np.asarray(triangle[2:4], np.float32),
                  np.asarray(triangle[4:6], np.float32)]
        if any(not (6 < p[0] < 506 and 6 < p[1] < 506) for p in points):
            continue
        midpoint = sum(points) / 3.0
        local = midpoint - centre
        ellipse_radius = np.hypot(local[0] / 205.0, local[1] / 174.0)
        if ellipse_radius > 1.03:
            continue
        for edge_index in range(3):
            a, b = points[edge_index], points[(edge_index + 1) % 3]
            if np.linalg.norm(a - b) < 61:
                _draw_line(m["shell_cages"], a, b, 1.0, 2)
        if tri_index % 3 == 0:
            inset = [midpoint + (point - midpoint) * 0.54 for point in points]
            _draw_poly(m["inner_cages"], inset, 1.0, 2, False, True)
        if tri_index % 4 == 1:
            cv2.circle(m["polygon_pores"], tuple(np.rint(midpoint).astype(int)),
                       2, 1.0, 2, cv2.LINE_AA)
        if tri_index % 5 == 2:
            vertex = points[tri_index % 3]
            _draw_line(m["radial_struts"], midpoint, vertex, 1.0, 2)
        tri_index += 1
    boundary = []
    for index in range(72):
        theta = -np.pi + index * _TAU / 72.0
        if -0.44 < theta < 0.36:
            continue
        warp = 1.0 + 0.08 * np.sin(3.0 * theta) + 0.05 * np.sin(7.0 * theta)
        point = centre + np.asarray([205.0 * warp * np.cos(theta),
                                     174.0 * (2.0 - warp) * np.sin(theta)], np.float32)
        boundary.append((point, theta, index))
    for point, theta, index in boundary:
        cv2.circle(m["spine_roots"], tuple(np.rint(point).astype(int)),
                   2, 1.0, -1, cv2.LINE_AA)
        direction = point - centre
        direction /= max(1.0, float(np.linalg.norm(direction)))
        length = 8 + (index * 7) % 19
        tip = point + direction * length
        _draw_line(m["tapered_spines"], point, tip, 1.0, 2 + index % 2)
        if index % 9 == 4:
            cv2.circle(m["broken_sockets"], tuple(np.rint(point).astype(int)),
                       4, 1.0, 2, cv2.LINE_AA)
    for theta in (-0.44, 0.36):
        rupture = centre + np.asarray([205.0 * np.cos(theta),
                                       174.0 * np.sin(theta)], np.float32)
        cv2.ellipse(m["aperture_collars"], tuple(np.rint(rupture).astype(int)),
                    (8, 4), np.degrees(theta), 0, 310, 1.0, 3, cv2.LINE_AA)
        cv2.circle(m["broken_sockets"], tuple(np.rint(rupture).astype(int)),
                   5, 1.0, 2, cv2.LINE_AA)
    x, y = _xy()
    tone = _norm((x - y) / 512.0 + np.sin((x + y) / 47.0))
    banks = dict(shell_cages="A", polygon_pores="B", radial_struts="A",
                 inner_cages="B", spine_roots="A", tapered_spines="B",
                 broken_sockets="N", aperture_collars="B")
    metal = _f32(0.05 + 0.61 * m["radial_struts"] + 0.55 * m["spine_roots"]
                 + 0.43 * m["shell_cages"] + 0.20 * tone)
    rough = _f32(0.10 + 0.62 * m["polygon_pores"] + 0.56 * m["broken_sockets"]
                 + 0.41 * m["inner_cages"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["tapered_spines"] + 0.59 * m["aperture_collars"]
                + 0.44 * m["inner_cages"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_amber_moldring() -> _Grammar:
    """Many small eccentric mold zones grow, collide and rupture along fronts."""
    names = ("colony_cores", "zoned_growth_rings", "fuzzy_fronts", "sector_wedges",
             "inhibition_halos", "spore_rims", "collision_scars", "rupture_scars")
    m = _new_marks(*names)
    centres = []
    for branch in range(7):
        base_radius = 218.0 - branch * 27.0
        for step in range(78):
            if (step + branch * 9) % 29 in (0, 1, 2):
                continue
            theta = step * _TAU / 78.0 + branch * 0.17
            radius = (base_radius + 18.0 * np.sin(3.0 * theta + branch)
                      + 11.0 * np.sin(5.0 * theta - branch * 0.7))
            centre = np.asarray([258 + np.cos(theta) * radius,
                                 257 + np.sin(theta) * radius * 0.76], np.float32)
            if 12 < centre[0] < 500 and 12 < centre[1] < 500:
                centres.append((centre, branch, step))
    # Colony-lined fjords connect selected cortex bands; unlike the rejected
    # trellis, every cross-link terminates in the same causal mold coastline.
    for fjord in range(11):
        theta = fjord * 0.57 + 0.23
        for step in range(13):
            radius = 52.0 + step * 12.5
            wobble = theta + 0.12 * np.sin(step * 0.73 + fjord)
            centre = np.asarray([258 + np.cos(wobble) * radius,
                                 257 + np.sin(wobble) * radius * 0.76], np.float32)
            if 12 < centre[0] < 500 and 12 < centre[1] < 500:
                centres.append((centre, 7 + fjord, step))
    for centre, branch, step in centres:
        cx, cy = map(int, centre)
        outer = 6 + (branch * 3 + step) % 8
        cv2.circle(m["colony_cores"], (cx, cy), 3, 1.0, -1, cv2.LINE_AA)
        for ring_index, radius in enumerate(range(4, outer + 1, 3)):
            offset = ((ring_index % 3) - 1, ((ring_index + branch) % 3) - 1)
            cv2.ellipse(m["zoned_growth_rings"], (cx + offset[0], cy + offset[1]),
                        (radius, max(4, radius - 2)), branch * 17, 0, 360, 1.0, 2, cv2.LINE_AA)
        cv2.ellipse(m["fuzzy_fronts"], (cx, cy), (outer + 2, outer), branch * 13,
                    8, 168, 1.0, 3, cv2.LINE_AA)
        cv2.ellipse(m["sector_wedges"], (cx, cy), (outer - 2, outer - 3),
                    step * 29, 12, 74, 1.0, 3, cv2.LINE_AA)
        cv2.ellipse(m["inhibition_halos"], (cx, cy), (outer + 5, outer + 3),
                    branch * 11, 194, 342, 1.0, 2, cv2.LINE_AA)
        cv2.circle(m["spore_rims"], (cx + outer // 2, cy - outer // 3), 2,
                   1.0, 2, cv2.LINE_AA)
        if step % 3 == 1:
            _draw_line(m["collision_scars"], (cx - outer, cy + 2),
                       (cx + outer, cy - 2), 1.0, 2)
        if step % 4 == 2:
            cv2.ellipse(m["rupture_scars"], (cx, cy), (outer, outer - 2),
                        branch * 19, 235, 310, 1.0, 3, cv2.LINE_AA)
    x, y = _xy()
    tone = _norm(np.sin(x / 37.0) + np.cos(y / 31.0) + (x + y) / 389.0)
    banks = dict(colony_cores="A", zoned_growth_rings="A", fuzzy_fronts="B",
                 sector_wedges="B", inhibition_halos="N", spore_rims="B",
                 collision_scars="N", rupture_scars="N")
    metal = _f32(0.05 + 0.61 * m["colony_cores"] + 0.54 * m["zoned_growth_rings"]
                 + 0.44 * m["collision_scars"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["inhibition_halos"] + 0.55 * m["collision_scars"]
                 + 0.42 * m["rupture_scars"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["fuzzy_fronts"] + 0.59 * m["sector_wedges"]
                + 0.45 * m["spore_rims"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_violet_chains() -> _Grammar:
    """Budding yeast chains form knotted branching graphs with closed loops."""
    names = ("yeast_bodies", "daughter_buds", "bud_necks", "mother_scars",
             "closed_loops", "branch_nodes", "terminal_buds", "ruptured_links")
    m = _new_marks(*names)
    roots = ((66, 72), (176, 38), (330, 64), (451, 113),
             (84, 288), (237, 244), (401, 301), (160, 442), (352, 456))
    for root_index, root in enumerate(roots):
        if root_index:
            _draw_line(m["bud_necks"], roots[root_index - 1], root, 0.58, 2)
        paths = [(np.asarray(root, np.float32), root_index * 0.71)]
        generation_count = 3 + root_index % 3
        for generation in range(generation_count):
            next_paths = []
            for start, angle in paths:
                previous = start
                step_count = 5 + (root_index + generation * 2) % 5
                for step in range(step_count):
                    bend = angle + 0.24 * np.sin(step * 0.8 + root_index + generation)
                    point = previous + np.asarray([np.cos(bend), np.sin(bend)]) * 8.0
                    point = np.clip(point, 6, 505)
                    cv2.ellipse(m["yeast_bodies"], tuple(np.rint(point).astype(int)),
                                (4, 3), np.degrees(bend), 0, 360, 1.0, 2, cv2.LINE_AA)
                    _draw_line(m["bud_necks"], previous, point, 1.0, 2)
                    if step % 2 == 0:
                        side = bend + (-1 if (step + generation) & 1 else 1) * 1.0
                        bud = point + np.asarray([np.cos(side), np.sin(side)]) * 6
                        cv2.circle(m["daughter_buds"], tuple(np.rint(bud).astype(int)),
                                   3, 1.0, -1, cv2.LINE_AA)
                    if step % 3 == 1:
                        cv2.circle(m["mother_scars"], tuple(np.rint(point).astype(int)),
                                   2, 1.0, 2, cv2.LINE_AA)
                    previous = point
                cv2.circle(m["branch_nodes"], tuple(np.rint(previous).astype(int)),
                           3, 1.0, -1, cv2.LINE_AA)
                if generation < generation_count - 1:
                    next_paths.append((previous, angle + 0.54 + 0.07 * root_index))
                    if (generation + root_index) % 3 != 0:
                        next_paths.append((previous, angle - 0.61 - 0.03 * generation))
                else:
                    cv2.circle(m["terminal_buds"], tuple(np.rint(previous).astype(int)),
                               4, 1.0, 2, cv2.LINE_AA)
            paths = next_paths
        cv2.ellipse(m["closed_loops"], root, (18 + root_index % 4 * 3, 11 + root_index % 3 * 2),
                    root_index * 23, 0, 285, 1.0, 2, cv2.LINE_AA)
        cv2.ellipse(m["ruptured_links"], root, (22, 15), root_index * 17,
                    305, 348, 1.0, 3, cv2.LINE_AA)
    x, y = _xy()
    tone = _norm(np.sin((x + y) / 41.0) + np.cos((x - y) / 47.0))
    banks = dict(yeast_bodies="A", daughter_buds="B", bud_necks="N",
                 mother_scars="A", closed_loops="B", branch_nodes="A",
                 terminal_buds="B", ruptured_links="N")
    metal = _f32(0.05 + 0.61 * m["yeast_bodies"] + 0.54 * m["mother_scars"]
                 + 0.44 * m["branch_nodes"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["ruptured_links"] + 0.54 * m["bud_necks"]
                 + 0.42 * m["mother_scars"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["daughter_buds"] + 0.58 * m["closed_loops"]
                + 0.46 * m["terminal_buds"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_cyan_colony() -> _Grammar:
    """Two unlike colony lobes interlock across one living S-shaped seam."""
    names = ("mother_colonies", "daughter_satellites", "bridge_necks",
             "division_fronts", "void_halos", "radial_channels", "shed_cells",
             "collision_boundaries")
    m = _new_marks(*names)
    seam = []
    for sample in range(151):
        t = sample / 150.0
        point = np.asarray([
            252.0 + 92.0 * np.sin(2.0 * np.pi * t + 0.31)
            + 24.0 * np.sin(5.0 * np.pi * t),
            13.0 + 486.0 * t,
        ], np.float32)
        seam.append(point)
    _draw_poly(m["collision_boundaries"], seam, 1.0, 4, False, False)
    nodes = []
    anchors = (5, 13, 22, 34, 47, 55, 69, 82, 96, 111, 123, 137, 146)
    for anchor_number, seam_index in enumerate(anchors):
        origin = seam[seam_index]
        tangent = seam[min(150, seam_index + 2)] - seam[max(0, seam_index - 2)]
        tangent /= max(1.0, float(np.linalg.norm(tangent)))
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        for side in (-1, 1):
            angle = float(np.arctan2(normal[1] * side, normal[0] * side))
            parent = origin.copy()
            steps = 5 + (anchor_number * 3 + side) % 7
            for step in range(1, steps + 1):
                bend = angle + 0.31 * np.sin(step * 0.77 + anchor_number * 1.13 + side)
                distance = 13.0 + (anchor_number + step * 2) % 8
                centre = parent + np.asarray([np.cos(bend), np.sin(bend)]) * distance
                centre += tangent * np.sin(step * 1.17 + anchor_number) * 4.0
                if not (7 < centre[0] < 505 and 7 < centre[1] < 505):
                    break
                _draw_line(m["bridge_necks"], parent, centre, 1.0, 2)
                nodes.append((centre, step + anchor_number, bend, side))
                if step in (2, 4) and (anchor_number + step) % 3 != 0:
                    fork_angle = bend + side * (0.67 + 0.06 * step)
                    fork = centre + np.asarray([np.cos(fork_angle),
                                                np.sin(fork_angle)]) * (9 + step)
                    _draw_line(m["bridge_necks"], centre, fork, 1.0, 2)
                    nodes.append((fork, step + anchor_number + 31,
                                  fork_angle, side))
                parent = centre
    for index, (centre, generation, angle, side) in enumerate(nodes):
        cx, cy = map(int, centre)
        radius = 2 + (index + generation) % 4
        cv2.ellipse(m["mother_colonies"], (cx, cy),
                    (radius + (side > 0), radius + (side < 0)),
                    np.degrees(angle), 0, 360, 1.0, 2, cv2.LINE_AA)
        cv2.ellipse(m["division_fronts"], (cx, cy), (radius + 3, radius + 1),
                    np.degrees(angle), 17, 153 + (index % 4) * 17,
                    1.0, 2, cv2.LINE_AA)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        _draw_line(m["radial_channels"], centre - normal * radius,
                   centre + normal * radius, 1.0, 2)
        sat = centre + normal * side * (radius + 6 + index % 4)
        cv2.circle(m["daughter_satellites"], tuple(np.rint(sat).astype(int)),
                   2 + index % 2, 1.0, -1, cv2.LINE_AA)
        if index % 3 == 0:
            cv2.ellipse(m["void_halos"], (cx, cy), (radius + 5, radius + 3),
                        np.degrees(angle), 194, 342, 1.0, 2, cv2.LINE_AA)
        if index % 5 == 1:
            shed = centre - tangent * (radius + 7)
            cv2.circle(m["shed_cells"], tuple(np.rint(shed).astype(int)),
                       2, 1.0, -1, cv2.LINE_AA)
    x, y = _xy()
    tone = _norm(x / 512.0 + np.sin(y / 43.0) + np.cos((x + y) / 61.0))
    banks = dict(mother_colonies="A", daughter_satellites="B", bridge_necks="N",
                 division_fronts="B", void_halos="N", radial_channels="A",
                 shed_cells="B", collision_boundaries="N")
    metal = _f32(0.05 + 0.61 * m["mother_colonies"] + 0.54 * m["radial_channels"]
                 + 0.45 * m["collision_boundaries"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["void_halos"] + 0.55 * m["collision_boundaries"]
                 + 0.41 * m["bridge_necks"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.66 * m["daughter_satellites"] + 0.59 * m["division_fronts"]
                + 0.45 * m["shed_cells"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_lime_mold() -> _Grammar:
    """One veined fungal umbrella rises from a rhizomorphic root crown."""
    names = ("hyphal_mats", "branch_forks", "spore_heads", "conidia_chains",
             "fruiting_rims", "clear_lanes", "dead_zones", "anastomosis_bridges")
    m = _new_marks(*names)
    cap = []
    for sample in range(181):
        t = sample / 180.0
        theta = np.pi + np.pi * t
        x = 256.0 + 217.0 * np.cos(theta)
        y = 270.0 + 184.0 * np.sin(theta)
        y += 9.0 * np.sin(sample * 0.49) + 5.0 * np.sin(sample * 1.07)
        cap.append(np.asarray([x, y], np.float32))
    underside = []
    for sample in range(91):
        t = sample / 90.0
        x = 39.0 + 434.0 * t
        y = 270.0 + 34.0 * np.sin(np.pi * t) + 7.0 * np.sin(sample * 0.61)
        underside.append(np.asarray([x, y], np.float32))
    _draw_poly(m["hyphal_mats"], cap, 1.0, 4, False, False)
    _draw_poly(m["hyphal_mats"], underside, 1.0, 4, False, False)

    # Intertwined stem bundles and roots establish the umbrella silhouette.
    for bundle in range(7):
        stem = []
        for sample in range(67):
            t = sample / 66.0
            stem.append(np.asarray([
                256.0 + (bundle - 3) * 4.2 * (1.0 - 0.45 * t)
                + 9.0 * np.sin(t * 2.0 * np.pi + bundle * 0.71),
                503.0 - 224.0 * t,
            ], np.float32))
        _draw_poly(m["hyphal_mats"], stem, 1.0, 2 + bundle % 2, False, False)
        for band in (14 + bundle, 31 + bundle % 3, 49 + bundle % 5):
            _draw_line(m["clear_lanes"], stem[band] + [-4, 0], stem[band] + [4, 0],
                       1.0, 2)
        root = stem[0]
        for side in (-1, 1):
            angle = 1.95 + side * (0.46 + bundle * 0.04)
            end = root + np.asarray([np.cos(angle), np.sin(angle)]) * (31 + bundle * 4)
            _draw_line(m["branch_forks"], root, end, 1.0, 2)

    # A non-ribbed dendritic cap vasculature grows from one hub and repeatedly
    # forks; tips meet the irregular cap rim instead of forming parallel gills.
    hub = np.asarray([256, 270], np.float32)
    frontier = [(hub, -2.96), (hub, -2.45), (hub, -1.89),
                (hub, -1.25), (hub, -0.68), (hub, -0.18)]
    tips = []
    for generation in range(6):
        next_frontier = []
        for lineage, (start, angle) in enumerate(frontier):
            previous = start
            for step in range(4 + (lineage + generation) % 4):
                bend = angle + 0.18 * np.sin(step * 0.93 + lineage + generation)
                point = previous + np.asarray([np.cos(bend), np.sin(bend)]) * (
                    9.0 + (step + lineage) % 4)
                if not (36 < point[0] < 476 and 81 < point[1] < 304):
                    break
                _draw_line(m["branch_forks"], previous, point, 1.0, 2)
                previous = point
            tips.append((previous, angle, lineage + generation * 19))
            if generation < 5:
                spread = 0.34 + 0.04 * generation
                next_frontier.append((previous, angle - spread))
                if (lineage + generation) % 3:
                    next_frontier.append((previous, angle + spread * 0.83))
        frontier = next_frontier
    for tip_index, (tip, angle, lineage) in enumerate(tips):
        centre = tuple(np.rint(tip).astype(int))
        if tip_index % 2 == 0:
            cv2.circle(m["spore_heads"], centre, 3 + lineage % 3,
                       1.0, -1, cv2.LINE_AA)
            cv2.ellipse(m["fruiting_rims"], centre,
                        (5 + lineage % 3, 3 + (lineage + 1) % 3),
                        lineage * 17, 0, 324, 1.0, 2, cv2.LINE_AA)
        for bead in range(1, 3 + lineage % 3):
            bead_angle = angle + 0.73 + 0.11 * bead
            p = tip + np.asarray([np.cos(bead_angle), np.sin(bead_angle)]) * bead * 4
            cv2.circle(m["conidia_chains"], tuple(np.rint(p).astype(int)),
                       2, 1.0, -1, cv2.LINE_AA)
        if tip_index % 9 == 3:
            cv2.ellipse(m["dead_zones"], centre, (7, 4), lineage * 13,
                        0, 291, 1.0, 2, cv2.LINE_AA)
    for left, right in ((3, 11), (17, 25), (31, 44), (52, 66), (73, 89)):
        if right < len(tips):
            _draw_line(m["anastomosis_bridges"], tips[left][0], tips[right][0],
                       1.0, 2)
    x, y = _xy()
    tone = _norm(np.hypot((x - 256) / 1.3, y - 235) / 371.0
                 + np.sin((x + y) / 53.0))
    banks = dict(hyphal_mats="A", branch_forks="A", spore_heads="B",
                 conidia_chains="B", fruiting_rims="B", clear_lanes="N",
                 dead_zones="N", anastomosis_bridges="A")
    metal = _f32(0.05 + 0.61 * m["hyphal_mats"] + 0.54 * m["branch_forks"]
                 + 0.43 * m["anastomosis_bridges"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["clear_lanes"] + 0.55 * m["dead_zones"]
                 + 0.42 * m["fruiting_rims"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.66 * m["spore_heads"] + 0.59 * m["conidia_chains"]
                + 0.45 * m["fruiting_rims"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_amber_diatom() -> _Grammar:
    """Seven isolated needle nests tangle without becoming woven slabs."""
    names = ("needle_valves", "raphe_grooves", "transverse_striae",
             "terminal_nodules", "girdle_seams", "crossed_felt_ribs",
             "broken_tips", "silica_pores")
    m = _new_marks(*names)
    for bundle in range(23):
        cx = 256 + 53 * np.sin(bundle * 1.47)
        cy = 256 + 47 * np.cos(bundle * 1.19)
        rx = 92 + (bundle * 17) % 137
        ry = 49 + (bundle * 23) % 89
        rotation = -1.13 + bundle * 0.287
        start_angle = bundle * 0.41
        sweep = 3.7 + (bundle % 5) * 0.31
        spine_points = []
        for step in range(52):
            phase = start_angle + sweep * step / 51.0
            local = np.asarray([np.cos(phase) * rx,
                                np.sin(phase) * ry], np.float32)
            ca, sa = np.cos(rotation), np.sin(rotation)
            p = np.asarray([cx + ca * local[0] - sa * local[1],
                            cy + sa * local[0] + ca * local[1]], np.float32)
            if not (8 < p[0] < 504 and 8 < p[1] < 504):
                continue
            derivative = np.asarray([-np.sin(phase) * rx,
                                     np.cos(phase) * ry], np.float32)
            tangent = np.asarray([ca * derivative[0] - sa * derivative[1],
                                  sa * derivative[0] + ca * derivative[1]])
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]])
            length = 6 + (step + bundle) % 7
            a = p - tangent * length
            b = p + tangent * length
            spine_points.append(p)
            _draw_line(m["needle_valves"], a, b, 1.0, 3)
            _draw_line(m["raphe_grooves"], a + normal * 2, b + normal * 2, 1.0, 2)
            for band in (-0.55, 0.0, 0.55):
                c = p + tangent * length * band
                _draw_line(m["transverse_striae"], c - normal * 3, c + normal * 3,
                           1.0, 2)
            cv2.circle(m["terminal_nodules"], tuple(np.rint(a).astype(int)),
                       2, 1.0, -1, cv2.LINE_AA)
            if step % 5 == 0:
                cv2.circle(m["silica_pores"], tuple(np.rint(b).astype(int)),
                           2, 1.0, 2, cv2.LINE_AA)
            if (step + bundle) % 9 == 0:
                _draw_line(m["broken_tips"], b - normal * 3, b + normal * 3, 1.0, 2)
            if step % 4 == 0:
                _draw_line(m["girdle_seams"], p - normal * 3, p + normal * 3, 1.0, 2)
        if len(spine_points) > 8:
            ordered = [spine_points[index] for index in range(0, len(spine_points), 5)]
            _draw_poly(m["crossed_felt_ribs"], ordered, 1.0, 2, False, False)
    x, y = _xy()
    tone = _norm(np.sin((x + y) / 31.0) + np.cos((x - y) / 43.0))
    banks = dict(needle_valves="A", raphe_grooves="N", transverse_striae="B",
                 terminal_nodules="A", girdle_seams="B", crossed_felt_ribs="A",
                 broken_tips="N", silica_pores="B")
    metal = _f32(0.05 + 0.61 * m["needle_valves"] + 0.54 * m["crossed_felt_ribs"]
                 + 0.44 * m["terminal_nodules"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["raphe_grooves"] + 0.55 * m["broken_tips"]
                 + 0.41 * m["girdle_seams"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["transverse_striae"] + 0.59 * m["silica_pores"]
                + 0.45 * m["girdle_seams"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_magenta_radiolaria() -> _Grammar:
    """Faceted cages occupy an angular constellation web, never radial arms."""
    names = ("polyhedral_shells", "polygon_pores", "radial_struts",
             "nested_inner_frames", "spine_roots", "tapering_spines",
             "aperture_collars", "broken_spine_sockets")
    m = _new_marks(*names)
    paths = (
        ((17, 447), (83, 318), (161, 357), (229, 221), (326, 264),
         (394, 132), (493, 77)),
        ((83, 318), (29, 209), (106, 128), (51, 34)),
        ((161, 357), (109, 444), (172, 501)),
        ((229, 221), (158, 156), (213, 75), (178, 7)),
        ((326, 264), (401, 327), (359, 419), (428, 506)),
        ((394, 132), (464, 197), (505, 166)),
        ((109, 128), (183, 116), (274, 159), (326, 264)),
        ((172, 501), (264, 452), (359, 419)),
        ((51, 34), (151, 42), (213, 75)),
    )
    centres = []
    for branch, anchors in enumerate(paths):
        anchors = [np.asarray(point, np.float32) for point in anchors]
        previous_centre = None
        for segment in range(len(anchors) - 1):
            start, end = anchors[segment], anchors[segment + 1]
            for substep in range(5):
                t = substep / 5.0
                centre = start * (1.0 - t) + end * t
                direction = end - start
                direction /= max(1.0, float(np.linalg.norm(direction)))
                normal = np.asarray([-direction[1], direction[0]], np.float32)
                centre += normal * 5.0 * np.sin((segment * 5 + substep) * 1.31 + branch)
                if 12 < centre[0] < 500 and 12 < centre[1] < 500:
                    step = segment * 5 + substep
                    centres.append((centre, branch, step))
                    if previous_centre is not None:
                        _draw_line(m["polyhedral_shells"], previous_centre, centre,
                                   0.72, 2)
                    previous_centre = centre
    for index, (centre, branch, step) in enumerate(centres):
        cx, cy = centre
        radius = 7 + (branch + step) % 4
        symmetry = 5 + (branch + 2 * step) % 3
        angle0 = branch * 0.41 + step * 0.27
        outer = []
        inner = []
        for vertex in range(symmetry):
            a = angle0 + vertex * _TAU / symmetry
            outer.append((cx + np.cos(a) * radius, cy + np.sin(a) * radius))
            inner.append((cx + np.cos(a + 0.18) * (radius - 3),
                          cy + np.sin(a + 0.18) * (radius - 3)))
        _draw_poly(m["polyhedral_shells"], outer, 1.0, 2, False, True)
        _draw_poly(m["nested_inner_frames"], inner, 1.0, 2, False, True)
        for vertex, point in enumerate(outer):
            _draw_line(m["radial_struts"], inner[vertex], point, 1.0, 2)
            cv2.circle(m["spine_roots"], tuple(map(int, point)), 2, 1.0, -1, cv2.LINE_AA)
            a = angle0 + vertex * _TAU / symmetry
            tip = (cx + np.cos(a) * (radius + 7), cy + np.sin(a) * (radius + 7))
            if vertex != (branch + step) % symmetry:
                _draw_line(m["tapering_spines"], point, tip, 1.0, 2)
            else:
                cv2.circle(m["broken_spine_sockets"], tuple(map(int, point)),
                           3, 1.0, 2, cv2.LINE_AA)
            if vertex % 2 == 0:
                pore = (int((point[0] + cx) * 0.5), int((point[1] + cy) * 0.5))
                cv2.circle(m["polygon_pores"], pore, 2, 1.0, 2, cv2.LINE_AA)
        cv2.ellipse(m["aperture_collars"], tuple(np.rint(centre).astype(int)),
                    (radius + 2, radius - 1), np.degrees(angle0), 190, 330,
                    1.0, 2, cv2.LINE_AA)
    x, y = _xy()
    tone = _norm((x + 0.4 * y) / 512.0 + np.sin((x - y) / 61.0))
    banks = dict(polyhedral_shells="A", polygon_pores="B", radial_struts="A",
                 nested_inner_frames="B", spine_roots="A", tapering_spines="B",
                 aperture_collars="B", broken_spine_sockets="N")
    metal = _f32(0.05 + 0.61 * m["polyhedral_shells"] + 0.55 * m["radial_struts"]
                 + 0.44 * m["spine_roots"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["polygon_pores"] + 0.55 * m["broken_spine_sockets"]
                 + 0.41 * m["nested_inner_frames"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["tapering_spines"] + 0.59 * m["aperture_collars"]
                + 0.45 * m["nested_inner_frames"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_cyan_mold() -> _Grammar:
    """One continuous mycelial knot crosses, heals and fruits."""
    names = ("primary_hyphae", "side_branches", "anastomosis_bridges",
             "conidia_beads", "active_tips", "empty_lacunae", "dead_end_scars",
             "growth_bands")
    m = _new_marks(*names)
    knot = []
    for sample in range(1201):
        t = sample * _TAU / 1200.0
        # Coprime lobes create a single closed biological knot.  It has no
        # nested lane ancestry and no independent kidney silhouette.
        point = np.asarray([
            256.0 + 205.0 * np.sin(3.0 * t + 0.29)
            + 31.0 * np.sin(8.0 * t),
            256.0 + 183.0 * np.sin(4.0 * t)
            + 27.0 * np.cos(7.0 * t + 0.41),
        ], np.float32)
        knot.append(np.clip(point, 8, 504))
    previous = knot[0]
    for sample, point in enumerate(knot[1:], 1):
        if sample % 113 not in (0, 1, 2, 3):
            _draw_line(m["primary_hyphae"], previous, point, 1.0, 3)
        previous = point
    branch_tips = []
    branch_samples = []
    cursor = 11
    branch_counter = 0
    while cursor < 1191:
        branch_samples.append(cursor)
        cursor += 9 + (branch_counter * 7) % 15
        branch_counter += 1
    for branch_index, sample in enumerate(branch_samples):
        origin = knot[sample]
        tangent = knot[(sample + 4) % 1201] - knot[(sample - 4) % 1201]
        tangent /= max(1.0, float(np.linalg.norm(tangent)))
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        side = -1 if branch_index & 1 else 1
        points = [origin]
        for step in range(1, 5 + branch_index % 7):
            point = origin + normal * side * step * (4.7 + branch_index % 3)
            point += tangent * np.sin(step * 0.91 + branch_index) * (4 + step * 0.4)
            points.append(np.clip(point, 5, 507))
        _draw_poly(m["side_branches"], points, 1.0, 2, False, False)
        tip = points[-1]
        branch_tips.append(tip)
        cv2.circle(m["active_tips"], tuple(np.rint(tip).astype(int)),
                   2 + branch_index % 2, 1.0, -1, cv2.LINE_AA)
        for bead in range(1, 3 + branch_index % 4):
            bead_point = tip + tangent * bead * 4.0
            cv2.circle(m["conidia_beads"], tuple(np.rint(bead_point).astype(int)),
                       2, 1.0, -1, cv2.LINE_AA)
        centre = points[2 + branch_index % (len(points) - 3)]
        cv2.ellipse(m["empty_lacunae"], tuple(np.rint(centre).astype(int)),
                    (5 + branch_index % 4, 3 + (branch_index + 1) % 3),
                    branch_index * 29, 0, 318, 1.0, 2, cv2.LINE_AA)
        local = points[min(len(points) - 1, 4)] - points[1]
        local /= max(1.0, float(np.linalg.norm(local)))
        cross = np.asarray([-local[1], local[0]], np.float32)
        _draw_line(m["growth_bands"], centre - cross * 4,
                   centre + cross * 4, 1.0, 2)
        if branch_index % 4 == 1:
            cv2.circle(m["dead_end_scars"], tuple(np.rint(points[-2]).astype(int)),
                       3, 1.0, 2, cv2.LINE_AA)
    # Dense crossing-local hyphal fans make the knot biologically legible at
    # car scale without adding another parallel carrier path.
    for fan_index, sample in enumerate(range(27, 1184, 47)):
        origin = knot[sample]
        tangent = knot[(sample + 5) % 1201] - knot[(sample - 5) % 1201]
        tangent /= max(1.0, float(np.linalg.norm(tangent)))
        base_angle = float(np.arctan2(tangent[1], tangent[0]))
        fan_tips = []
        branch_count = 2 + fan_index % 4
        for branch in range(branch_count):
            angle = (base_angle - 1.19 + branch * 2.38 / max(1, branch_count - 1)
                     + 0.17 * np.sin(fan_index + branch))
            previous = origin
            for step in range(1, 4 + (fan_index + branch) % 4):
                point = previous + np.asarray([np.cos(angle), np.sin(angle)]) * (
                    6 + (fan_index + step + branch) % 5)
                _draw_line(m["side_branches"], previous, point, 1.0, 2)
                previous = point
            fan_tips.append(previous)
            cv2.circle(m["active_tips"], tuple(np.rint(previous).astype(int)),
                       2, 1.0, -1, cv2.LINE_AA)
            if (fan_index + branch) % 2 == 0:
                cv2.circle(m["conidia_beads"],
                           tuple(np.rint(previous + tangent * 4).astype(int)),
                           2, 1.0, -1, cv2.LINE_AA)
        if len(fan_tips) > 2 and fan_index % 3:
            _draw_poly(m["anastomosis_bridges"], fan_tips,
                       1.0, 2, False, False)
    for left in range(1, len(branch_tips) - 17, 4):
        right = left + 11 + (left * 5) % 13
        if right >= len(branch_tips):
            continue
        a, b = branch_tips[left], branch_tips[right]
        if np.linalg.norm(a - b) < 132:
            midpoint = (a + b) * 0.5 + np.asarray([7 * np.sin(left),
                                                   7 * np.cos(right)], np.float32)
            _draw_poly(m["anastomosis_bridges"], (a, midpoint, b),
                       1.0, 2, False, False)
    x, y = _xy()
    tone = _norm(np.hypot(x - 268, y - 262) / 351.0 +
                 np.sin((x - y) / 47.0))
    banks = dict(primary_hyphae="A", side_branches="A", anastomosis_bridges="B",
                 conidia_beads="B", active_tips="B", empty_lacunae="N",
                 dead_end_scars="N", growth_bands="A")
    metal = _f32(0.05 + 0.61 * m["primary_hyphae"] + 0.54 * m["growth_bands"]
                 + 0.44 * m["side_branches"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["empty_lacunae"] + 0.55 * m["dead_end_scars"]
                 + 0.41 * m["growth_bands"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["conidia_beads"] + 0.59 * m["active_tips"]
                + 0.45 * m["anastomosis_bridges"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_amber_plankton() -> _Grammar:
    """One colonial siphonophore coils, branches and sheds feeding polyps."""
    names = ("segmented_ribbons", "hinge_joints", "segment_bands", "cilia_combs",
             "eye_spots", "paired_wakes", "wake_curls", "broken_fragments")
    m = _new_marks(*names)
    coil = []
    tangents = []
    for sample in range(1381):
        t = sample / 1380.0
        theta = -0.73 + t * np.pi * 4.72
        radius = 13.0 + 192.0 * t + 8.0 * np.sin(theta * 2.7)
        moving_centre = np.asarray([218.0 + 78.0 * t,
                                    308.0 - 74.0 * t], np.float32)
        point = moving_centre + np.asarray([radius * np.cos(theta),
                                            radius * np.sin(theta) * 0.78],
                                           np.float32)
        derivative = np.asarray([
            78.0 / (np.pi * 4.72) + 192.0 / (np.pi * 4.72) * np.cos(theta)
            - radius * np.sin(theta),
            (-74.0 / (np.pi * 4.72) + 192.0 / (np.pi * 4.72) * np.sin(theta)
             + radius * np.cos(theta)) * 0.78,
        ], np.float32)
        derivative /= max(1.0, float(np.linalg.norm(derivative)))
        coil.append(point)
        tangents.append(derivative)
    for sample in range(1, len(coil)):
        if sample % 181 not in (0, 1, 2, 3, 4, 5):
            _draw_line(m["segmented_ribbons"], coil[sample - 1], coil[sample],
                       1.0, 4)
    polyp_samples = []
    cursor = 17
    polyp_counter = 0
    while cursor < 1368:
        polyp_samples.append(cursor)
        cursor += 13 + (polyp_counter * 5) % 14
        polyp_counter += 1
    for polyp_index, sample in enumerate(polyp_samples):
        centre = coil[sample]
        tangent = tangents[sample]
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        _draw_line(m["segment_bands"], centre - normal * (4 + polyp_index % 3),
                   centre + normal * (4 + polyp_index % 3), 1.0, 2)
        cv2.circle(m["hinge_joints"], tuple(np.rint(centre).astype(int)),
                   2 + polyp_index % 2, 1.0, -1, cv2.LINE_AA)
        side = -1 if polyp_index & 1 else 1
        branch = [centre]
        for step in range(1, 6 + polyp_index % 4):
            point = centre + normal * side * step * (4.2 + polyp_index % 3)
            point += tangent * np.sin(step * 0.83 + polyp_index) * 5.0
            branch.append(point)
        archetype = polyp_index % 5
        if archetype == 0:
            _draw_poly(m["segmented_ribbons"], branch, 1.0, 3, False, False)
        elif archetype == 1:
            _draw_poly(m["segmented_ribbons"], branch[:4], 1.0, 2, False, False)
            cv2.ellipse(m["segmented_ribbons"], tuple(np.rint(branch[-1]).astype(int)),
                        (7 + polyp_index % 4, 4 + polyp_index % 3),
                        np.degrees(np.arctan2(tangent[1], tangent[0])),
                        0, 360, 1.0, 3, cv2.LINE_AA)
        elif archetype == 2:
            _draw_poly(m["segmented_ribbons"], branch, 1.0, 2, False, False)
            fork_normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            _draw_line(m["segmented_ribbons"], branch[-2],
                       branch[-1] + fork_normal * 8, 1.0, 2)
            _draw_line(m["segmented_ribbons"], branch[-2],
                       branch[-1] - fork_normal * 8, 1.0, 2)
        elif archetype == 3:
            sail = (branch[1], branch[-1] + tangent * 7,
                    branch[-1] + normal * side * 8)
            _draw_poly(m["segmented_ribbons"], sail, 1.0, 2, False, True)
        else:
            microcoil = []
            for coil_step in range(31):
                phase = coil_step * 0.41 + polyp_index
                radius = 1.0 + coil_step * 0.19
                microcoil.append(branch[-1] + np.asarray([
                    np.cos(phase) * radius, np.sin(phase) * radius], np.float32))
            _draw_poly(m["segmented_ribbons"], microcoil, 1.0, 2, False, False)
        tip = branch[-1]
        cv2.ellipse(m["eye_spots"], tuple(np.rint(tip).astype(int)),
                    (3 + polyp_index % 3, 2),
                    np.degrees(np.arctan2(tangent[1], tangent[0])),
                    0, 360, 1.0, -1, cv2.LINE_AA)
        for branch_step in range(1, len(branch) - 1, 2):
            p = branch[branch_step]
            _draw_line(m["cilia_combs"], p, p + tangent * side * (5 + branch_step % 3),
                       1.0, 2)
        for wake_side in (-1, 1):
            a = tip + normal * wake_side * 3
            b = a - tangent * (8 + polyp_index % 7)
            _draw_line(m["paired_wakes"], a, b, 1.0, 2)
        curl = tip - tangent * (11 + polyp_index % 5)
        cv2.ellipse(m["wake_curls"], tuple(np.rint(curl).astype(int)),
                    (5 + polyp_index % 3, 2 + polyp_index % 2),
                    np.degrees(np.arctan2(tangent[1], tangent[0])),
                    31, 287, 1.0, 2, cv2.LINE_AA)
        if polyp_index % 4 == 2:
            scar = coil[max(0, sample - 17)]
            _draw_line(m["broken_fragments"], scar - normal * 5,
                       scar + normal * 5, 1.0, 3)
    x, y = _xy()
    tone = _norm(np.sin((x + y) / 47.0) + np.cos((x - y) / 59.0))
    banks = dict(segmented_ribbons="A", hinge_joints="N", segment_bands="B",
                 cilia_combs="B", eye_spots="A", paired_wakes="A",
                 wake_curls="B", broken_fragments="N")
    metal = _f32(0.05 + 0.61 * m["segmented_ribbons"] + 0.54 * m["eye_spots"]
                 + 0.44 * m["paired_wakes"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["hinge_joints"] + 0.55 * m["broken_fragments"]
                 + 0.41 * m["segment_bands"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["cilia_combs"] + 0.59 * m["wake_curls"]
                + 0.45 * m["segment_bands"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_violet_membrane() -> _Grammar:
    """One folded figure-eight bilayer forms a literal membrane knot."""
    names = ("bilayer_saddles", "connected_channels", "saddle_patches",
             "neck_rings", "protein_rods", "transmembrane_pores",
             "cleavage_domains", "vesicle_buds")
    masks = _new_marks(*names)
    centreline = []
    normals = []
    for sample in range(1201):
        t = sample * _TAU / 1200.0
        point = np.asarray([
            256.0 + 216.0 * np.sin(t) + 17.0 * np.sin(5.0 * t),
            256.0 + 168.0 * np.sin(2.0 * t) + 13.0 * np.cos(7.0 * t),
        ], np.float32)
        derivative = np.asarray([
            216.0 * np.cos(t) + 85.0 * np.cos(5.0 * t),
            336.0 * np.cos(2.0 * t) - 91.0 * np.sin(7.0 * t),
        ], np.float32)
        derivative /= max(1.0, float(np.linalg.norm(derivative)))
        normal = np.asarray([-derivative[1], derivative[0]], np.float32)
        centreline.append(point)
        normals.append(normal)
    for side in (-1, 1):
        leaflet = [point + normals[index] * side * (4.0 + 0.8 * np.sin(index * 0.037))
                   for index, point in enumerate(centreline)]
        for sample in range(1, len(leaflet)):
            if (sample + (side > 0) * 43) % 173 not in (0, 1, 2, 3, 4):
                _draw_line(masks["bilayer_saddles"], leaflet[sample - 1],
                           leaflet[sample], 1.0, 3)
    event_samples = []
    cursor = 13
    event_counter = 0
    while cursor < 1191:
        event_samples.append(cursor)
        cursor += 11 + (event_counter * 7) % 17
        event_counter += 1
    for event_index, sample in enumerate(event_samples):
        point = centreline[sample]
        normal = normals[sample]
        tangent = np.asarray([normal[1], -normal[0]], np.float32)
        a, b = point - normal * 5.0, point + normal * 5.0
        _draw_line(masks["connected_channels"], a, b, 1.0,
                   2 + event_index % 2)
        cv2.ellipse(masks["neck_rings"], tuple(np.rint(point).astype(int)),
                    (4 + event_index % 3, 3 + (event_index + 1) % 2),
                    float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                    0, 360, 1.0, 2, cv2.LINE_AA)
        protein = point + tangent * (((event_index * 7) % 9) - 4)
        _draw_line(masks["protein_rods"], protein - normal * 7,
                   protein + normal * 7, 1.0, 2)
        pore = point + tangent * (4 + event_index % 5)
        cv2.circle(masks["transmembrane_pores"], tuple(np.rint(pore).astype(int)),
                   2, 1.0, 2, cv2.LINE_AA)
        if event_index % 3 == 0:
            bud = point + normal * (10 + event_index % 6)
            cv2.circle(masks["vesicle_buds"], tuple(np.rint(bud).astype(int)),
                       4 + event_index % 3, 1.0, 2, cv2.LINE_AA)
            _draw_line(masks["saddle_patches"], point, bud, 1.0, 2)
        if event_index % 4 == 1:
            scar = point - tangent * (6 + event_index % 4)
            cv2.ellipse(masks["cleavage_domains"], tuple(np.rint(scar).astype(int)),
                        (6, 3), event_index * 21, 15, 298, 1.0, 2,
                        cv2.LINE_AA)
        else:
            _draw_line(masks["saddle_patches"], point - tangent * 5,
                       point + tangent * 5, 1.0, 2)
        if event_index % 5 == 2:
            partner_index = (sample + 173 + event_index * 19) % 1200
            partner = centreline[partner_index]
            if np.linalg.norm(partner - point) < 148:
                chord_normal = np.asarray([-(partner - point)[1],
                                           (partner - point)[0]], np.float32)
                chord_normal /= max(1.0, float(np.linalg.norm(chord_normal)))
                midpoint = (point + partner) * 0.5 + chord_normal * (
                    ((event_index * 13) % 23) - 11)
                _draw_poly(masks["connected_channels"],
                           (point, midpoint, partner), 1.0, 2, False, False)
                cv2.circle(masks["transmembrane_pores"],
                           tuple(np.rint(midpoint).astype(int)),
                           2, 1.0, 2, cv2.LINE_AA)
    for cluster_index, sample in enumerate(range(29, 1182, 41)):
        origin = centreline[sample]
        normal = normals[sample]
        tangent = np.asarray([normal[1], -normal[0]], np.float32)
        side = -1 if cluster_index & 1 else 1
        previous = origin
        for bud_index in range(1, 3 + cluster_index % 4):
            bud = origin + normal * side * (8 + bud_index * (5 + cluster_index % 3))
            bud += tangent * np.sin(bud_index * 0.91 + cluster_index) * (
                4 + cluster_index % 5)
            radius = 2 + (cluster_index + bud_index) % 4
            cv2.circle(masks["vesicle_buds"], tuple(np.rint(bud).astype(int)),
                       radius, 1.0, 2, cv2.LINE_AA)
            _draw_line(masks["saddle_patches"], previous, bud, 1.0, 2)
            if bud_index % 2:
                cv2.circle(masks["transmembrane_pores"],
                           tuple(np.rint(bud).astype(int)),
                           2, 1.0, -1, cv2.LINE_AA)
            previous = bud
    banks = dict(bilayer_saddles="A", connected_channels="B", saddle_patches="A",
                 neck_rings="B", protein_rods="B", transmembrane_pores="N",
                 cleavage_domains="N", vesicle_buds="A")
    x, y = _xy()
    tone = _norm(np.sin((x + y) / 43.0) + np.cos((x - 2.0 * y) / 71.0))
    metal = _f32(0.05 + 0.61 * masks["bilayer_saddles"]
                 + 0.54 * masks["saddle_patches"]
                 + 0.44 * masks["vesicle_buds"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * masks["cleavage_domains"]
                 + 0.55 * masks["transmembrane_pores"]
                 + 0.41 * masks["connected_channels"]
                 + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * masks["connected_channels"]
                + 0.59 * masks["neck_rings"] + 0.45 * masks["protein_rods"]
                + 0.18 * tone)
    return _pack(masks, banks, tone, metal, rough, coat)


def _build_fpe_lime_chains() -> _Grammar:
    """Six cocci lineages braid around one serpentine living helix."""
    names = ("cocci_bodies", "division_septa", "contact_flats", "chain_bends",
             "branch_forks", "terminal_cells", "division_scars", "broken_links")
    m = _new_marks(*names)
    cell_index = 0
    phases = tuple(step * _TAU / 6.0 for step in range(6))
    for route_index, phase in enumerate(phases):
        points = []
        for sample in range(2200):
            t = sample / 2199.0
            axis = np.asarray([256 + 171 * np.sin(3.0 * np.pi * t + 0.27)
                               + 43 * np.sin(7.0 * np.pi * t),
                               18 + 476 * t], np.float32)
            derivative = np.asarray([
                171 * 3.0 * np.pi * np.cos(3.0 * np.pi * t + 0.27)
                + 43 * 7.0 * np.pi * np.cos(7.0 * np.pi * t),
                476.0], np.float32)
            tangent = derivative / max(1.0, float(np.linalg.norm(derivative)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            offset = normal * (18.0 + 5.0 * np.sin(5.0 * np.pi * t)) * np.sin(
                23.0 * np.pi * t + phase)
            points.append(axis + offset)
        previous_cell = None
        stride = 8 + route_index
        for sample in range(0, len(points), stride):
            point = points[sample]
            before = points[(sample - 3) % len(points)]
            after = points[(sample + 3) % len(points)]
            tangent = after - before
            length = max(1.0, float(np.linalg.norm(tangent)))
            tangent /= length
            normal = np.asarray([-tangent[1], tangent[0]])
            centre = tuple(np.rint(point).astype(int))
            if cell_index % (41 + route_index) in (0, 1):
                cv2.circle(m["broken_links"], centre, 4, 1.0, 2, cv2.LINE_AA)
                previous_cell = None
                cell_index += 1
                continue
            cv2.circle(m["cocci_bodies"], centre, 3, 1.0, -1, cv2.LINE_AA)
            _draw_line(m["division_septa"], point - normal * 3,
                       point + normal * 3, 1.0, 2)
            if previous_cell is not None and np.linalg.norm(point - previous_cell) < 17:
                _draw_line(m["contact_flats"], previous_cell, point, 1.0, 2)
            if cell_index % 13 == 0:
                cv2.circle(m["chain_bends"], centre, 4, 1.0, 2, cv2.LINE_AA)
            if cell_index % 29 == 7:
                fork = point + normal * (10 + cell_index % 7)
                _draw_line(m["branch_forks"], point, fork, 1.0, 2)
                cv2.circle(m["terminal_cells"], tuple(np.rint(fork).astype(int)),
                           3, 1.0, -1, cv2.LINE_AA)
            if cell_index % 17 == 5:
                cv2.circle(m["division_scars"], centre, 2, 1.0, 2, cv2.LINE_AA)
            previous_cell = point
            cell_index += 1
    x, y = _xy()
    tone = _norm(np.sin((x + y) / 37.0) + np.cos((x - y) / 53.0))
    banks = dict(cocci_bodies="A", division_septa="B", contact_flats="N",
                 chain_bends="A", branch_forks="B", terminal_cells="B",
                 division_scars="N", broken_links="N")
    metal = _f32(0.05 + 0.61 * m["cocci_bodies"] + 0.54 * m["chain_bends"]
                 + 0.44 * m["division_scars"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["broken_links"] + 0.55 * m["contact_flats"]
                 + 0.41 * m["division_septa"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["branch_forks"] + 0.59 * m["terminal_cells"]
                + 0.45 * m["division_septa"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_violet_frustule() -> _Grammar:
    """One asymmetric cathedral frustule carries branching silica tracery."""
    names = ("centric_valves", "central_rosettes", "areola_rows",
             "marginal_spines", "ring_bands", "rimoportula_pores",
             "radial_costae", "broken_sectors")
    m = _new_marks(*names)
    left_arch = []
    right_arch = []
    for sample in range(121):
        t = sample / 120.0
        left_arch.append(np.asarray([
            78.0 + 178.0 * t + 17.0 * np.sin(np.pi * t),
            470.0 - 421.0 * t + 39.0 * np.sin(np.pi * t),
        ], np.float32))
        right_arch.append(np.asarray([
            439.0 - 183.0 * t - 11.0 * np.sin(np.pi * t),
            470.0 - 421.0 * t + 24.0 * np.sin(np.pi * t),
        ], np.float32))
    outline = left_arch + list(reversed(right_arch))
    _draw_poly(m["centric_valves"], outline, 1.0, 4, False, True)
    inner_left = [np.asarray([103, 447], np.float32) * (1 - t)
                  + np.asarray([256, 79], np.float32) * t
                  + np.asarray([13 * np.sin(np.pi * t), 21 * np.sin(np.pi * t)])
                  for t in np.linspace(0, 1, 89)]
    inner_right = [np.asarray([410, 447], np.float32) * (1 - t)
                   + np.asarray([256, 79], np.float32) * t
                   + np.asarray([-9 * np.sin(np.pi * t), 14 * np.sin(np.pi * t)])
                   for t in np.linspace(0, 1, 89)]
    _draw_poly(m["ring_bands"], inner_left, 1.0, 2, False, False)
    _draw_poly(m["ring_bands"], inner_right, 1.0, 2, False, False)
    for index in range(5, 117, 6):
        for arch in (left_arch, right_arch):
            cv2.circle(m["areola_rows"], tuple(np.rint(arch[index]).astype(int)),
                       2, 1.0, 2, cv2.LINE_AA)
    for index in (13, 27, 38, 54, 67, 83, 101, 113):
        inner_index = min(88, int(index * 88 / 120))
        _draw_line(m["ring_bands"], left_arch[index], inner_left[inner_index],
                   1.0, 2)
        _draw_line(m["ring_bands"], right_arch[index], inner_right[inner_index],
                   1.0, 2)
    knots = (np.asarray([151, 377], np.float32), np.asarray([342, 397], np.float32),
             np.asarray([207, 291], np.float32), np.asarray([311, 254], np.float32),
             np.asarray([252, 166], np.float32), np.asarray([256, 76], np.float32))
    for knot_index, knot in enumerate(knots):
        sides = 5 + knot_index % 3
        radius = 5 + knot_index % 4
        rosette = [knot + np.asarray([np.cos(knot_index * 0.41 + side * _TAU / sides),
                                      np.sin(knot_index * 0.41 + side * _TAU / sides)])
                   * radius for side in range(sides)]
        _draw_poly(m["central_rosettes"], rosette, 1.0, 2, False, True)
        cv2.circle(m["rimoportula_pores"], tuple(np.rint(knot).astype(int)),
                   2, 1.0, -1, cv2.LINE_AA)
    links = ((0, 2), (0, 3), (1, 2), (1, 3), (2, 4), (3, 4), (4, 5))
    tracery_segments = []
    for link_index, (a_index, b_index) in enumerate(links):
        a, b = knots[a_index], knots[b_index]
        normal = np.asarray([-(b - a)[1], (b - a)[0]], np.float32)
        normal /= max(1.0, float(np.linalg.norm(normal)))
        midpoint = (a + b) * 0.5 + normal * (((link_index * 13) % 19) - 9)
        _draw_poly(m["radial_costae"], (a, midpoint, b), 1.0, 3, False, False)
        tracery_segments.extend(((a, midpoint), (midpoint, b)))
    rim_targets = (left_arch[19], right_arch[24], left_arch[42], right_arch[51],
                   left_arch[68], right_arch[73], left_arch[91], right_arch[97])
    for target_index, target in enumerate(rim_targets):
        source = knots[target_index % 5]
        bend = (source + target) * 0.5 + np.asarray([
            ((target_index * 17) % 23) - 11,
            ((target_index * 29) % 31) - 15,
        ], np.float32)
        _draw_poly(m["radial_costae"], (source, bend, target),
                   1.0, 2, False, False)
        tracery_segments.extend(((source, bend), (bend, target)))
    seed_angles = (-1.23, -1.88, -0.79, -2.34, 0.38, 2.74)
    frontier = [(knots[index], seed_angles[index], index)
                for index in range(len(knots))]
    branch_serial = 0
    for generation in range(5):
        next_frontier = []
        for start, angle, ancestry in frontier:
            previous = start
            survived = True
            for step in range(3 + (ancestry + generation) % 4):
                bend = angle + 0.21 * np.sin(step * 0.87 + ancestry * 0.61
                                             + generation)
                point = previous + np.asarray([np.cos(bend), np.sin(bend)]) * (
                    12 + (branch_serial + step) % 8)
                if not (56 < point[1] < 463):
                    survived = False
                    break
                half_width = 16.0 + (point[1] - 49.0) * 0.43
                if not (256.0 - half_width < point[0] < 256.0 + half_width):
                    survived = False
                    break
                _draw_line(m["radial_costae"], previous, point, 1.0, 2)
                tracery_segments.append((previous, point))
                if (branch_serial + step) % 3 == 0:
                    cv2.circle(m["areola_rows"], tuple(np.rint(point).astype(int)),
                               2, 1.0, 2, cv2.LINE_AA)
                previous = point
            if survived and generation < 4:
                spread = 0.43 + generation * 0.07
                next_frontier.append((previous, angle - spread,
                                      ancestry * 2 + 1))
                if (ancestry + generation + branch_serial) % 3:
                    next_frontier.append((previous, angle + spread * 0.89,
                                          ancestry * 2 + 2))
            if branch_serial % 7 == 2:
                cv2.circle(m["rimoportula_pores"],
                           tuple(np.rint(previous).astype(int)),
                           2, 1.0, -1, cv2.LINE_AA)
            if branch_serial % 11 == 4:
                cv2.ellipse(m["ring_bands"], tuple(np.rint(previous).astype(int)),
                            (6 + generation, 3 + generation % 3),
                            branch_serial * 17, 0, 307, 1.0, 2, cv2.LINE_AA)
            branch_serial += 1
        frontier = next_frontier
    pore_index = 0
    for start, end in tracery_segments:
        for step in range(2, 9, 2 + pore_index % 2):
            t = step / 10.0
            point = start * (1.0 - t) + end * t
            cv2.circle(m["areola_rows"], tuple(np.rint(point).astype(int)),
                       2, 1.0, 2, cv2.LINE_AA)
            pore_index += 1
    for index in range(7, 114, 9):
        for side, arch in ((-1, left_arch), (1, right_arch)):
            point = arch[index]
            tangent = arch[min(120, index + 2)] - arch[max(0, index - 2)]
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32) * side
            _draw_line(m["marginal_spines"], point, point + normal * (7 + index % 9),
                       1.0, 2)
    fracture = (np.asarray([311, 254]), np.asarray([357, 214]),
                np.asarray([385, 173]), np.asarray([413, 151]))
    _draw_poly(m["broken_sectors"], fracture, 1.0, 4, False, False)
    x, y = _xy()
    tone = _norm(np.sin(x / 43.0) + np.cos(y / 47.0) + (x + y) / 407.0)
    banks = dict(centric_valves="A", central_rosettes="B", areola_rows="B",
                 marginal_spines="B", ring_bands="A", rimoportula_pores="N",
                 radial_costae="B", broken_sectors="N")
    metal = _f32(0.05 + 0.61 * m["centric_valves"] + 0.54 * m["ring_bands"]
                 + 0.44 * m["rimoportula_pores"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["broken_sectors"] + 0.55 * m["areola_rows"]
                 + 0.41 * m["centric_valves"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["radial_costae"] + 0.59 * m["marginal_spines"]
                + 0.45 * m["central_rosettes"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fpe_magenta_plankton() -> _Grammar:
    """A seven-species trophic reef grows around one bent nutrient scaffold."""
    names = ("bell_jellies", "spiral_flagellates", "needle_diatoms",
             "feeding_tethers", "cilia_crowns", "vacuole_eyes", "shed_cysts",
             "feeding_knots")
    m = _new_marks(*names)
    anchors = (np.asarray([67, 79], np.float32), np.asarray([168, 118], np.float32),
               np.asarray([287, 75], np.float32), np.asarray([418, 132], np.float32),
               np.asarray([355, 246], np.float32), np.asarray([449, 372], np.float32),
               np.asarray([302, 451], np.float32), np.asarray([181, 391], np.float32),
               np.asarray([74, 307], np.float32), np.asarray([143, 227], np.float32),
               np.asarray([254, 268], np.float32))
    tether_links = ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
                    (6, 7), (7, 8), (8, 9), (9, 0), (9, 10), (10, 4),
                    (10, 7), (1, 10))
    for link_index, (a_index, b_index) in enumerate(tether_links):
        a, b = anchors[a_index], anchors[b_index]
        normal = np.asarray([-(b - a)[1], (b - a)[0]], np.float32)
        normal /= max(1.0, float(np.linalg.norm(normal)))
        midpoint = (a + b) * 0.5 + normal * (((link_index * 17) % 29) - 14)
        _draw_poly(m["feeding_tethers"], (a, midpoint, b), 1.0,
                   2 + link_index % 2, False, False)
        cv2.circle(m["feeding_knots"], tuple(np.rint(midpoint).astype(int)),
                   2 + link_index % 3, 1.0, -1, cv2.LINE_AA)
    # Three unrelated organism mechanisms share the causal food web.  Bells,
    # flagellate coils and silica needles are individually varied rather than
    # a single icon stamped along streamlines.
    for jelly_index, anchor_index in enumerate((0, 4, 7, 9)):
        centre = anchors[anchor_index]
        rx, ry = 12 + jelly_index * 3, 7 + (jelly_index * 5) % 8
        angle = -24 + jelly_index * 37
        cv2.ellipse(m["bell_jellies"], tuple(np.rint(centre).astype(int)),
                    (rx, ry), angle, 178, 354, 1.0, 3, cv2.LINE_AA)
        for tentacle in range(4 + jelly_index):
            start = centre + np.asarray([(tentacle - (3 + jelly_index) / 2) * 4.0,
                                         ry * 0.5], np.float32)
            points = [start]
            for step in range(1, 7):
                points.append(start + np.asarray([
                    4.0 * np.sin(step * 0.91 + tentacle + jelly_index),
                    step * (4.0 + jelly_index * 0.4),
                ], np.float32))
            _draw_poly(m["cilia_crowns"], points, 1.0, 2, False, False)
        eye = centre + np.asarray([(-1 if jelly_index & 1 else 1) * 5, -2])
        cv2.circle(m["vacuole_eyes"], tuple(np.rint(eye).astype(int)),
                   2 + jelly_index % 2, 1.0, -1, cv2.LINE_AA)
    for coil_index, anchor_index in enumerate((1, 5, 8)):
        centre = anchors[anchor_index]
        points = []
        for step in range(67):
            theta = step * (0.17 + coil_index * 0.013)
            radius = 2.0 + step * (0.17 + coil_index * 0.025)
            points.append(centre + np.asarray([np.cos(theta) * radius,
                                               np.sin(theta) * radius * 0.72]))
        _draw_poly(m["spiral_flagellates"], points, 1.0, 2, False, False)
        for step in (19, 37, 55):
            cv2.circle(m["shed_cysts"], tuple(np.rint(points[step]).astype(int)),
                       2 + (step + coil_index) % 2, 1.0, 2, cv2.LINE_AA)
    needle_centres = ((anchors[2], -0.71), (anchors[3], 0.42),
                      (anchors[6], -2.31), (anchors[10], 1.17))
    for group_index, (centre, base_angle) in enumerate(needle_centres):
        for needle in range(7 + group_index):
            angle = base_angle + (needle - 3) * (0.19 + group_index * 0.015)
            offset = np.asarray([np.cos(angle + 1.4), np.sin(angle + 1.4)]) * (
                5 + needle * 4)
            midpoint = centre + offset
            tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            length = 8 + (needle * 3 + group_index) % 13
            _draw_line(m["needle_diatoms"], midpoint - tangent * length,
                       midpoint + tangent * length, 1.0, 3)
            for band in (-0.5, 0.0, 0.5):
                p = midpoint + tangent * length * band
                _draw_line(m["cilia_crowns"], p - normal * 3, p + normal * 3,
                           1.0, 2)
            cv2.circle(m["vacuole_eyes"], tuple(np.rint(midpoint).astype(int)),
                       2, 1.0, -1, cv2.LINE_AA)
            if (needle + group_index) % 3 == 0:
                cv2.circle(m["shed_cysts"], tuple(np.rint(midpoint + normal * 7).astype(int)),
                           3, 1.0, 2, cv2.LINE_AA)
    golden = np.pi * (3.0 - np.sqrt(5.0))
    for habitat_index, habitat in enumerate(anchors):
        organism_count = 17 + habitat_index % 7
        for organism in range(organism_count):
            u = organism / max(1.0, organism_count - 1.0)
            mode = habitat_index % 4
            if mode == 0:
                radius = 9.0 + 10.5 * np.sqrt(organism + 1)
                theta = organism * golden + habitat_index * 0.71
                local = np.asarray([np.cos(theta) * radius,
                                    np.sin(theta) * radius * 0.63], np.float32)
            elif mode == 1:
                theta = -2.4 + 4.7 * u + 0.13 * np.sin(organism * 1.31)
                radius = 31.0 + 13.0 * np.sin(organism * 1.73)
                local = np.asarray([np.cos(theta) * radius,
                                    np.sin(theta) * radius * 0.74], np.float32)
            elif mode == 2:
                theta = organism * golden + habitat_index * 0.43
                radius = 8.0 + 37.0 * np.sqrt(u)
                local = np.asarray([np.sin(2.0 * theta) * radius,
                                    np.sin(theta) * radius * 0.72], np.float32)
            else:
                theta = -1.17 + 2.34 * u
                axial = (u - 0.5) * 76.0
                local = np.asarray([axial + 8.0 * np.sin(organism * 0.91),
                                    np.sin(theta) * (18.0 + 21.0 * (1.0 - u))],
                                   np.float32)
            centre = habitat + local
            if not (8 < centre[0] < 504 and 8 < centre[1] < 504):
                continue
            species = (organism + habitat_index * 2) % 3
            angle = theta + 0.43 * np.sin(organism + habitat_index)
            tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            if species == 0:
                cv2.ellipse(m["bell_jellies"], tuple(np.rint(centre).astype(int)),
                            (5 + organism % 4, 3 + habitat_index % 3),
                            np.degrees(angle), 174, 356, 1.0, 2, cv2.LINE_AA)
                for tentacle in (-1, 0, 1):
                    start = centre + normal * tentacle * 3
                    end = start - tangent * (7 + (organism + tentacle) % 5)
                    _draw_line(m["cilia_crowns"], start, end, 1.0, 2)
            elif species == 1:
                coil = []
                for step in range(24):
                    phase = angle + step * (0.31 + habitat_index * 0.007)
                    local_radius = 1.5 + step * (0.16 + organism % 3 * 0.025)
                    coil.append(centre + np.asarray([np.cos(phase) * local_radius,
                                                     np.sin(phase) * local_radius]))
                _draw_poly(m["spiral_flagellates"], coil, 1.0, 2, False, False)
                _draw_line(m["cilia_crowns"], coil[-1],
                           coil[-1] + tangent * (6 + organism % 5), 1.0, 2)
            else:
                length = 6 + (organism * 3 + habitat_index) % 9
                _draw_line(m["needle_diatoms"], centre - tangent * length,
                           centre + tangent * length, 1.0, 2 + organism % 2)
                for band in (-0.45, 0.0, 0.45):
                    p = centre + tangent * length * band
                    _draw_line(m["cilia_crowns"], p - normal * 2,
                               p + normal * 2, 1.0, 2)
            if organism % 6 == 0:
                cv2.circle(m["feeding_knots"], tuple(np.rint(centre).astype(int)),
                           2, 1.0, -1, cv2.LINE_AA)
            if organism % 5 == 1:
                cv2.circle(m["vacuole_eyes"], tuple(np.rint(centre + normal * 3).astype(int)),
                           2, 1.0, -1, cv2.LINE_AA)
            if organism % 6 == 2:
                cv2.circle(m["shed_cysts"], tuple(np.rint(centre - tangent * 6).astype(int)),
                           2 + habitat_index % 2, 1.0, 2, cv2.LINE_AA)
    x, y = _xy()
    tone = _norm(np.sin((x + 2.0 * y) / 49.0) + np.cos((2.0 * x - y) / 67.0))
    banks = dict(bell_jellies="A", spiral_flagellates="B", needle_diatoms="A",
                 feeding_tethers="N", cilia_crowns="B", vacuole_eyes="A",
                 shed_cysts="B", feeding_knots="N")
    metal = _f32(0.05 + 0.61 * m["needle_diatoms"] + 0.54 * m["vacuole_eyes"]
                 + 0.44 * m["feeding_knots"] + 0.20 * tone)
    rough = _f32(0.10 + 0.63 * m["shed_cysts"] + 0.55 * m["feeding_tethers"]
                 + 0.41 * m["spiral_flagellates"] + 0.20 * (1.0 - tone))
    coat = _f32(0.05 + 0.65 * m["bell_jellies"] + 0.59 * m["cilia_crowns"]
                + 0.45 * m["spiral_flagellates"] + 0.18 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


# ---------------------------------------------------------------------------
# WR-P3 owner-eye replacements for the four W2 REPAIR cards.
#
# Owner verdict 2026-08-24: a new function/hash is irrelevant when the card is
# still one root, one ribbon, one diagonal graph, or one sparse loop carrier.
# These builders replace those complete canvas topologies.  They share only
# literal drawing/material plumbing; none shares a field, placement scaffold,
# contour carrier, or spec substrate.  W2 -> W3 metric movement is recorded by
# the candidate evidence after the contact sheet survives owner-eye review.


def _w3_curve(mask: np.ndarray, points, width=2, value=1.0) -> None:
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    cv2.polylines(mask, [pts], False, float(value), max(2, min(8, int(width))), cv2.LINE_AA)


def _w3_bezier(p0, p1, p2, p3, count=30):
    t = np.linspace(0.0, 1.0, int(count), dtype=np.float32)[:, None]
    return ((1 - t) ** 3 * np.asarray(p0, np.float32)
            + 3 * (1 - t) ** 2 * t * np.asarray(p1, np.float32)
            + 3 * (1 - t) * t ** 2 * np.asarray(p2, np.float32)
            + t ** 3 * np.asarray(p3, np.float32))


def _w3_phase_line(phase, half=0.16):
    d = np.abs(np.sin(np.pi * np.asarray(phase, np.float32)))
    return _f32((float(half) - d) / max(0.02, float(half)) + 0.24)


def _build_w3_fpe_magenta_bloom() -> _Grammar:
    """Four colliding DLA-like fronts; no point-rooted triangular crown."""
    m = _new_marks("primary_growth_fronts", "secondary_dendrites", "bud_rims",
                   "bud_cytoplasm", "fusion_bridges", "mutation_scars",
                   "nutrient_halation", "necrotic_tips", "cross_septa")
    terminals = []

    def grow(start, angle, length, depth, phase):
        p = np.asarray(start, np.float32)
        direction = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-direction[1], direction[0]], np.float32)
        end = p + direction * length + normal * (8.0 * np.sin(phase * 1.7))
        path = _w3_bezier(p, p + direction * length * .28 + normal * 9 * np.cos(phase),
                          p + direction * length * .71 - normal * 7 * np.sin(phase * 1.3),
                          end, 25)
        _w3_curve(m["primary_growth_fronts"] if depth >= 4 else m["secondary_dendrites"],
                  path, 2 + (depth >= 4) + (depth >= 5))
        if depth <= 0:
            terminals.append((end, phase))
            return end
        left = grow(end, angle - (.28 + .035 * depth), length * .71, depth - 1, phase + .83)
        right = grow(end, angle + (.41 - .026 * depth), length * .64, depth - 1, phase + 1.37)
        if depth in (2, 4):
            _w3_curve(m["fusion_bridges"], _w3_bezier(left, left + [8, -6],
                                                       right + [-9, 7], right, 18), 2)
        return end

    grow((-24, 76), .17, 95, 5, .4)
    grow((536, 168), 3.03, 91, 5, 1.7)
    grow((156, -24), 1.20, 86, 5, 2.8)
    grow((377, 536), -1.72, 90, 5, 4.1)
    for i, (p, phase) in enumerate(terminals):
        px, py = map(float, p)
        cv2.circle(m["bud_rims"], (int(px), int(py)), 4 + i % 3, 1.0, 2, cv2.LINE_AA)
        cv2.circle(m["bud_cytoplasm"], (int(px), int(py)), 2 + i % 2, 1.0, -1, cv2.LINE_AA)
        if i % 4 == 1:
            cv2.line(m["necrotic_tips"], (int(px - 5), int(py - 3)),
                     (int(px + 6), int(py + 4)), 1.0, 2, cv2.LINE_AA)
        if i % 3 == 0:
            cv2.ellipse(m["mutation_scars"], (int(px), int(py)), (7, 3),
                        int((phase * 31) % 180), 0, 270, 1.0, 2, cv2.LINE_AA)
    organism = np.maximum.reduce((m["primary_growth_fronts"], m["secondary_dendrites"],
                                  m["fusion_bridges"], m["bud_rims"]))
    m["nutrient_halation"][:] = _f32(cv2.GaussianBlur(organism, (0, 0), 4.0)
                                      - .20 * organism)
    x, y = _xy()
    m["cross_septa"][:] = _f32(_w3_phase_line((x + .37 * y) / 29.0, .10)
                                 * cv2.dilate(organism, np.ones((7, 7), np.uint8)))
    banks = dict(primary_growth_fronts="A", secondary_dendrites="B", bud_rims="A",
                 bud_cytoplasm="B", fusion_bridges="N", mutation_scars="A",
                 nutrient_halation="B", necrotic_tips="N", cross_septa="B")
    dist = cv2.distanceTransform((organism < .15).astype(np.uint8), cv2.DIST_L2, 5)
    tone = _norm(dist + .18 * x - .27 * y + 13 * m["mutation_scars"])
    metal = _f32(.04 + .88 * m["primary_growth_fronts"] + .71 * m["bud_rims"]
                 + .54 * m["mutation_scars"] + .31 * m["cross_septa"])
    rough = _f32(.08 + .86 * m["necrotic_tips"] + .68 * m["fusion_bridges"]
                 + .49 * m["nutrient_halation"] + .27 * m["bud_cytoplasm"])
    coat = _f32(.04 + .90 * m["secondary_dendrites"] + .77 * m["bud_cytoplasm"]
                + .57 * m["cross_septa"] + .33 * m["nutrient_halation"])
    return _pack(m, banks, tone, metal, rough, coat)


def _build_w3_fpe_cyan_membrane() -> _Grammar:
    """Quasiperiodic broken bilayer terrain; sheets own area, not a loop graph."""
    x, y = _xy()
    q = (np.sin((.89 * x + .31 * y) / 13.0)
         + .78 * np.sin((-.27 * x + 1.17 * y) / 17.0 + .9)
         + .61 * np.cos((.73 * x - .81 * y) / 23.0 + 2.1))
    v = np.sin((x + 1.618 * y) / 31.0) + np.cos((1.414 * x - y) / 37.0)
    leaflet_a = _f32((.34 - np.abs(q - .31)) / .12 + .45)
    leaflet_b = _f32((.34 - np.abs(q + .38)) / .12 + .45)
    exposed_ends = _f32(_edge(leaflet_a, 1) * (v > .35) + _edge(leaflet_b, 1) * (v < -.30))
    fusion_necks = _f32(_w3_phase_line(q * 1.7 + v * .33, .10)
                        * cv2.dilate(np.minimum(leaflet_a, leaflet_b), np.ones((5, 5), np.uint8)))
    rafts = _f32((v > .72).astype(np.float32) * (np.abs(q) < .72))
    gates = _f32(_w3_phase_line((x - .47 * y) / 19.0 + q * .21, .09)
                 * np.maximum(leaflet_a, leaflet_b))
    pores = _f32(_w3_phase_line((x + y) / 23.0, .08)
                 * _w3_phase_line(v * 2.4, .09) * (np.abs(q) < .80))
    rupture_lips = _edge(_f32((np.abs(v) < .13) * (np.abs(q) < 1.0)), 1)
    lipid_tails = _f32(_w3_phase_line((y + .18 * x) / 6.5 + .15 * q, .11)
                      * np.maximum(leaflet_a, leaflet_b))
    m = dict(outer_leaflet=leaflet_a, inner_leaflet=leaflet_b,
             exposed_bilayer_ends=exposed_ends, fusion_necks=fusion_necks,
             protein_rafts=rafts, gated_channels=gates, unequal_pores=pores,
             rupture_lips=rupture_lips, lipid_tail_pleats=lipid_tails)
    banks = dict(outer_leaflet="A", inner_leaflet="B", exposed_bilayer_ends="N",
                 fusion_necks="A", protein_rafts="B", gated_channels="A",
                 unequal_pores="B", rupture_lips="N", lipid_tail_pleats="B")
    tone = _norm(q + 1.7 * v + .003 * x)
    metal = _f32(.03 + .84 * leaflet_a + .74 * gates + .58 * fusion_necks
                 + .36 * exposed_ends)
    rough = _f32(.08 + .88 * rupture_lips + .67 * lipid_tails + .53 * pores + .31 * rafts)
    coat = _f32(.03 + .90 * leaflet_b + .78 * rafts + .59 * pores + .39 * lipid_tails)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_w3_fpe_lime_culture() -> _Grammar:
    """Affine Julia culture chronology; no three calligraphic macro ribbons."""
    x, y = _xy()
    zx = (x - 311.0 + .12 * (y - 244.0)) / 164.0
    zy = (y - 218.0 - .09 * (x - 260.0)) / 151.0
    z = (zx + 1j * zy) + .09 * np.sin(zy * 2.4)
    c = np.complex64(-.742 + .121j)
    alive = np.ones((_WORK, _WORK), bool)
    age = np.zeros((_WORK, _WORK), np.float32)
    orbit = np.zeros((_WORK, _WORK), np.float32)
    for i in range(22):
        z[alive] = z[alive] * z[alive] + c
        mag = np.abs(z)
        newly = alive & (mag > 2.3)
        age[newly] = float(i) + _norm(np.log1p(mag[newly])) if np.any(newly) else age[newly]
        alive &= ~newly
        orbit += np.exp(-np.abs(z - (.22 + .31j)) * 3.2).astype(np.float32)
    age[alive] = 23.0
    age = _norm(age)
    orbit = _norm(orbit)
    fronts = _w3_phase_line(age * 9.2 + .27 * orbit, .14)
    mutation = _f32(_w3_phase_line(orbit * 6.3 - age * 1.7, .11) * (age > .12))
    sheath = _f32((age > .54).astype(np.float32) * (orbit > .18))
    rupture = _edge(_f32((orbit > .63).astype(np.float32)), 1)
    sectors = _f32((np.sin(np.angle(z) * 5.0 + age * 7.0) > .42).astype(np.float32)
                   * (age > .20))
    satellites = _f32(_w3_phase_line((x - 1.31 * y) / 21.0, .08)
                      * _w3_phase_line(orbit * 4.8, .10))
    branch_cascades = _f32(_w3_phase_line((x + .22 * y) / 17.0 + age * 2.1, .09)
                           * (orbit > .26))
    lysis = _f32((age < .42).astype(np.float32) * (orbit > .22))
    m = dict(inoculation_fronts=fronts, mutation_sectors=mutation,
             living_sheath=sheath, sheath_ruptures=rupture,
             divergent_culture_sectors=sectors, satellite_colonies=satellites,
             local_branch_cascades=branch_cascades, lysis_bays=lysis)
    banks = dict(inoculation_fronts="A", mutation_sectors="B", living_sheath="A",
                 sheath_ruptures="N", divergent_culture_sectors="B",
                 satellite_colonies="A", local_branch_cascades="B", lysis_bays="N")
    tone = _norm(age + .77 * orbit + .05 * np.sin(np.angle(z)))
    metal = _f32(.04 + .86 * fronts + .72 * sheath + .56 * satellites + .34 * rupture)
    rough = _f32(.08 + .87 * lysis + .69 * rupture + .52 * mutation + .31 * branch_cascades)
    coat = _f32(.04 + .89 * sectors + .76 * branch_cascades + .58 * mutation + .36 * satellites)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_w3_fpe_cyan_colony() -> _Grammar:
    """Opposed tissue continents collide along one nonlinear necrotic seam."""
    x, y = _xy()
    seam = x - 248.0 + 48 * np.sin(y / 61.0) + 17 * np.sin(y / 23.0 + x / 97.0)
    left_body = _f32((-seam + 8.0) / 7.0 + .5)
    right_body = _f32((seam + 8.0) / 7.0 + .5)
    collision = _line(seam, 2.4)
    left_lobes = _f32(_w3_phase_line((y + 19 * np.sin(x / 43.0)) / 29.0, .11) * left_body)
    right_canals = _f32(_w3_phase_line((x + .38 * y + 13 * np.sin(y / 47.0)) / 23.0,
                                       .10) * right_body)
    necrotic_bays = _f32(_w3_phase_line(y / 47.0 + .31 * np.sin(y / 19.0), .10)
                         * (np.abs(seam) < 22))
    fold_lips = _edge(_f32((np.abs(seam) < 11 + 5 * np.sin(y / 37.0))), 1)
    bud_fronts = _f32(_w3_phase_line((x - y) / 19.0, .08) * (np.abs(seam) < 34))
    internal_bays = _f32(_w3_phase_line((x + 1.7 * y) / 41.0, .09)
                         * left_body * (1.0 - .55 * left_lobes))
    cross_feeders = _f32(_w3_phase_line((y - .17 * x) / 17.0, .09)
                         * right_body * (1.0 - .48 * right_canals))
    m = dict(left_colony_tissue=left_body, right_colony_tissue=right_body,
             nonlinear_collision_seam=collision, left_edge_folds=left_lobes,
             right_canal_network=right_canals, necrotic_bays=necrotic_bays,
             collision_fold_lips=fold_lips, bud_fronts=bud_fronts,
             left_internal_bays=internal_bays, right_cross_feeders=cross_feeders)
    banks = dict(left_colony_tissue="A", right_colony_tissue="B",
                 nonlinear_collision_seam="N", left_edge_folds="B",
                 right_canal_network="A", necrotic_bays="N",
                 collision_fold_lips="B", bud_fronts="A",
                 left_internal_bays="A", right_cross_feeders="B")
    tone = _norm(seam + 27 * left_lobes - 21 * right_canals + 9 * necrotic_bays)
    metal = _f32(.04 + .79 * left_body + .72 * right_canals + .58 * bud_fronts
                 + .39 * internal_bays)
    rough = _f32(.08 + .90 * necrotic_bays + .70 * collision + .56 * fold_lips
                 + .34 * cross_feeders)
    coat = _f32(.04 + .82 * right_body + .73 * left_lobes + .57 * cross_feeders
                + .38 * fold_lips)
    return _pack(m, banks, tone, metal, rough, coat)


_BUILDERS: Mapping[str, Callable[[], _Grammar]] = {
    "fpe_magenta_bloom": _build_w3_fpe_magenta_bloom,
    "fpe_cyan_membrane": _build_w3_fpe_cyan_membrane,
    "fpe_lime_culture": _build_w3_fpe_lime_culture,
    "fpe_amber_agar": _build_fpe_amber_agar,
    "fpe_violet_garden": _build_fpe_violet_garden,
    "fpe_lime_diatom": _build_fpe_lime_diatom,
    "fpe_magenta_mosaic": _build_fpe_magenta_mosaic,
    "fpe_cyan_spineball": _build_fpe_cyan_spineball,
    "fpe_amber_moldring": _build_fpe_amber_moldring,
    "fpe_violet_chains": _build_fpe_violet_chains,
    "fpe_cyan_colony": _build_w3_fpe_cyan_colony,
    "fpe_lime_mold": _build_fpe_lime_mold,
    "fpe_amber_diatom": _build_fpe_amber_diatom,
    "fpe_magenta_radiolaria": _build_fpe_magenta_radiolaria,
    "fpe_cyan_mold": _build_fpe_cyan_mold,
    "fpe_amber_plankton": _build_fpe_amber_plankton,
    "fpe_violet_membrane": _build_fpe_violet_membrane,
    "fpe_lime_chains": _build_fpe_lime_chains,
    "fpe_violet_frustule": _build_fpe_violet_frustule,
    "fpe_magenta_plankton": _build_fpe_magenta_plankton,
}


_HUES: Mapping[str, Tuple[float, float]] = {
    "fpe_magenta_bloom": (0.88, 0.42),
    "fpe_cyan_membrane": (0.50, 0.91),
    "fpe_lime_culture": (0.27, 0.77),
    "fpe_amber_agar": (0.09, 0.55),
    "fpe_violet_garden": (0.76, 0.34),
    "fpe_lime_diatom": (0.25, 0.79),
    "fpe_magenta_mosaic": (0.89, 0.44),
    "fpe_cyan_spineball": (0.52, 0.97),
    "fpe_amber_moldring": (0.10, 0.56),
    "fpe_violet_chains": (0.77, 0.30),
    "fpe_cyan_colony": (0.51, 0.91),
    "fpe_lime_mold": (0.28, 0.82),
    "fpe_amber_diatom": (0.08, 0.55),
    "fpe_magenta_radiolaria": (0.87, 0.47),
    "fpe_cyan_mold": (0.50, 0.94),
    "fpe_amber_plankton": (0.09, 0.51),
    "fpe_violet_membrane": (0.78, 0.37),
    "fpe_lime_chains": (0.27, 0.80),
    "fpe_violet_frustule": (0.75, 0.31),
    "fpe_magenta_plankton": (0.90, 0.46),
}


PETRI_IDS: Tuple[str, ...] = tuple(_BUILDERS)


if len(PETRI_IDS) != 20 or set(PETRI_IDS) != set(_HUES):
    raise AssertionError("Petri rebuild must own exactly its 20 configured IDs")
if len(set(_BUILDERS.values())) != 20:
    raise AssertionError("one separate builder function is required per Petri ID")


@lru_cache(maxsize=8)
def _authored(fid: str) -> Tuple[np.ndarray, np.ndarray]:
    if fid not in _BUILDERS:
        raise KeyError(fid)
    return _compose(_BUILDERS[fid](), _HUES[fid])


def clear_cache() -> None:
    _authored.cache_clear()
    _xy.cache_clear()


def debug_grammar(fid: str) -> _Grammar:
    if fid not in _BUILDERS:
        raise KeyError(fid)
    return _BUILDERS[fid]()


def debug_hue_null(fid: str) -> np.ndarray:
    """Palette-independent topology proof that a recolor cannot disguise."""
    grammar = debug_grammar(fid)
    out = np.full((_WORK, _WORK), 0.07, np.float32)
    levels = (0.28, 0.73, 0.43, 0.91, 0.57, 0.82, 0.35, 0.66, 0.97)
    for index, (_name, mask, owner) in enumerate(grammar.marks):
        level_index = index if owner != "B" else len(levels) - 1 - (index % len(levels))
        value = levels[level_index % len(levels)]
        out = out * (1.0 - mask) + value * mask
    return np.repeat(np.clip(out[..., None], 0, 1), 3, axis=2).astype(np.float32)


def debug_angle_pair(fid: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Controlled angle proof driven by independent finish-local M/R/Cc."""
    paint, spec = _authored(fid)
    grammar = debug_grammar(fid)
    owner_a = np.maximum.reduce(
        [mask for _name, mask, owner in grammar.marks if owner == "A"])
    owner_b = np.maximum.reduce(
        [mask for _name, mask, owner in grammar.marks if owner == "B"])
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - 0.50 * rough, 0.24, 1.0)
    lobe_a = np.clip(0.11 + 1.10 * metal * aperture + 0.34 * owner_a
                     - 0.10 * owner_b, 0.10, 1.24)
    lobe_b = np.clip(0.11 + 1.10 * coat * aperture + 0.34 * owner_b
                     - 0.10 * owner_a, 0.10, 1.24)
    warm = np.asarray([0.24, 0.075, 0.012], np.float32)
    cool = np.asarray([0.012, 0.105, 0.25], np.float32)
    angle_a = np.clip(paint * lobe_a[..., None]
                      + warm * (metal * aperture * (0.45 + 0.55 * owner_a))[..., None],
                      0, 1)
    angle_b = np.clip(paint * lobe_b[..., None]
                      + cool * (coat * aperture * (0.45 + 0.55 * owner_b))[..., None],
                      0, 1)
    diff = np.abs(angle_a - angle_b)
    return angle_a.astype(np.float32), angle_b.astype(np.float32), diff.astype(np.float32)


def _entry(fid: str):
    """Return the registry contract's required ``(spec_fn, paint_fn)`` tuple."""
    if fid not in _BUILDERS:
        raise KeyError(fid)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)
        if src.ndim != 3 or src.shape[2] < 3:
            src = np.zeros((fh, fw, 3), np.float32)
        else:
            src = src[:, :, :3]
            if src.size and float(np.max(src)) > 1.5:
                src = src / 255.0
            if src.shape[:2] != (fh, fw):
                src = cv2.resize(src, (fw, fh), interpolation=cv2.INTER_LINEAR)
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        authored, _ = _authored(fid)
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST)
        alpha = np.clip(m2 * max(0.0, float(pm)), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - alpha) + authored * alpha, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        _, authored = _authored(fid)
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        active = np.clip(_CALM_SPEC + (authored - _CALM_SPEC)
                         * max(0.0, float(sm)), 0, 255)
        mk = np.clip(m2, 0, 1)[..., None]
        rgb = active * mk + _CALM_SPEC * (1.0 - mk)
        out = np.empty((fh, fw, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    spec_fn.__name__ = f"spec_{fid}_petri_rejection_rebuild"
    paint_fn.__name__ = f"paint_{fid}_petri_rejection_rebuild"
    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Override exactly the 20 current Petri IDs in every live fusion registry."""
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    engine_module = _sys.modules.get("shokker_engine_v2")
    if engine_module is not None and hasattr(engine_module, "FUSION_REGISTRY"):
        regs.append(engine_module.FUSION_REGISTRY)
    unique_regs = []
    for registry in regs:
        if all(registry is not other for other in unique_regs):
            unique_regs.append(registry)
    for fid in PETRI_IDS:
        entry = _entry(fid)
        for registry in unique_regs:
            registry[fid] = entry
    return f"fractured-wilds-petri-rejection-candidate: {len(PETRI_IDS)} explicit grammars live"


__all__ = (
    "PETRI_IDS",
    "clear_cache",
    "debug_angle_pair",
    "debug_grammar",
    "debug_hue_null",
    "install_into_engine",
)
