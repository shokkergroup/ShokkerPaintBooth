# -*- coding: utf-8 -*-
"""Independent Fractured Petri owner-eye candidates -- wave I1.

This file is deliberately isolated from the registry and production renderer.
It starts with one finish because Petri W4--W10 proved that twenty mechanically
green builders can still be twenty bad pictures.  A candidate enters BUILDERS
only after its paint, hue-null, M, R, Cc and A/B contacts are inspected.

I1-01 reserves a physical topology not used by the other Wilds lanes:
``fpe_violet_chains`` is a continuous covalent polymer gel.  Its image comes
from persistent worm-like-chain trajectories and their chemistry -- never an
RNG/noise field, repeated tile, glyph stamp, lattice, radial hub or line-row
carrier.  Backbones, pi cores, strain sheaths, crosslinks, knot overpasses,
pendant groups, cyclic splices, radical gaps, oxidised caps and crystalline
stretches are all literal masks.  Every spec feature is written from that
anatomy; there is no shared rank map or shared spec substrate.

SPB-WILDS 2026-08-24, independent I1.  Owner doctrine: 8--32 px native marks,
5+ causal mark families, explicit Fractured A/B ownership.  Candidate only;
no owner acceptance or production wiring is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np


S = 512


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    hue_null: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]


def _f(value):
    return np.clip(np.asarray(value, np.float32), 0.0, 1.0)


def _n(value):
    value = np.nan_to_num(np.asarray(value, np.float32))
    lo, hi = float(value.min()), float(value.max())
    if hi - lo < 1.0e-7:
        return np.zeros(value.shape, np.float32)
    return ((value - lo) / (hi - lo)).astype(np.float32)


def _mask():
    return np.zeros((S, S), np.float32)


def _stroke(target, points, width, value=1.0, closed=False):
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape(-1, 1, 2)
    if len(pts) > 1:
        cv2.polylines(target, [pts], bool(closed), float(value),
                      max(2, min(8, int(width))), cv2.LINE_AA)


def _line(target, a, b, width, value=1.0):
    cv2.line(target, tuple(np.rint(a).astype(int)),
             tuple(np.rint(b).astype(int)), float(value),
             max(2, min(8, int(width))), cv2.LINE_AA)


def _circle(target, centre, radius, width=-1, value=1.0):
    cv2.circle(target, tuple(np.rint(centre).astype(int)),
               max(1, int(round(radius))), float(value), int(width), cv2.LINE_AA)


def _ellipse(target, centre, axes, angle, width=2, value=1.0):
    cv2.ellipse(target, tuple(np.rint(centre).astype(int)),
                tuple(np.maximum(1, np.rint(axes).astype(int))), float(angle),
                0.0, 360.0, float(value), int(width), cv2.LINE_AA)


def _dilate(value, radius):
    k = np.ones((2 * int(radius) + 1,) * 2, np.uint8)
    return _f(cv2.dilate(_f(value), k))


def _halo(value, sigma):
    return _f(cv2.GaussianBlur(_f(value), (0, 0), float(sigma)) - .22 * _f(value))


def _write_channel(base, masks, recipe):
    out = np.full((S, S), float(base), np.float32)
    for name, target in recipe:
        alpha = _f(masks[name])
        out = out * (1.0 - alpha) + float(target) * alpha
    return np.clip(out, 0.0, 255.0).astype(np.float32)


def _rgb(hex_value):
    value = hex_value.removeprefix("#")
    return np.asarray(tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)),
                      np.float32) / 255.0


def _blend(canvas, color, alpha):
    alpha = _f(alpha)[..., None]
    return canvas * (1.0 - alpha) + np.asarray(color, np.float32) * alpha


def _wormlike_chains():
    """Return deterministic persistent chains; no RNG and no scalar-noise field.

    A quasiperiodic curvature law supplies molecular thermal persistence while
    a divergence-free analytic drift couples neighbouring chains.  Boundary
    reflection keeps each molecule continuous instead of wrapping it into
    disconnected line fragments.
    """
    chains = []
    golden = (1.0 + 5.0 ** .5) * .5
    for chain_index in range(17):
        side = chain_index % 4
        along = ((chain_index * .61803398875) % 1.0) * (S - 48.0) + 24.0
        if side == 0:
            point = np.asarray((18.0, along), np.float64)
            heading = -.28 + .17 * np.sin(chain_index * golden)
        elif side == 1:
            point = np.asarray((S - 19.0, along), np.float64)
            heading = np.pi + .28 + .17 * np.sin(chain_index * golden)
        elif side == 2:
            point = np.asarray((along, 18.0), np.float64)
            heading = np.pi * .5 + .21 * np.cos(chain_index * golden)
        else:
            point = np.asarray((along, S - 19.0), np.float64)
            heading = -np.pi * .5 + .21 * np.cos(chain_index * golden)

        points = []
        for step in range(470):
            x, y = point / float(S)
            # Analytic incompressible drift from a two-mode stream function.
            phase = chain_index * .1732050808
            vx = (1.14 * np.sin(2.0 * np.pi * (x + phase))
                  * np.cos(2.0 * np.pi * (y - .37 * phase))
                  + .44 * np.cos(2.0 * np.pi * (2.0 * x - y + phase)))
            vy = (-1.14 * np.cos(2.0 * np.pi * (x + phase))
                  * np.sin(2.0 * np.pi * (y - .37 * phase))
                  + .88 * np.cos(2.0 * np.pi * (2.0 * x - y + phase)))
            field_angle = np.arctan2(vy, vx)
            delta = np.arctan2(np.sin(field_angle - heading),
                               np.cos(field_angle - heading))
            persistence = (.050 * np.sin(step * .1490712 + chain_index * 1.173)
                           + .031 * np.sin(step * .0618034 + chain_index * 2.071)
                           + .018 * np.cos(step * .2271073 - chain_index * .619))
            heading += .072 * delta + persistence
            step_length = 2.42 + .34 * np.sin(step * .097 + chain_index * .73)
            point = point + step_length * np.asarray((np.cos(heading),
                                                       np.sin(heading)))
            # Molecular reflection is explicit and preserves the chain path.
            if point[0] < 12.0 or point[0] > S - 13.0:
                point[0] = np.clip(point[0], 12.0, S - 13.0)
                heading = np.pi - heading
            if point[1] < 12.0 or point[1] > S - 13.0:
                point[1] = np.clip(point[1], 12.0, S - 13.0)
                heading = -heading
            points.append(point.copy())
        chains.append(np.asarray(points, np.float32))
    return tuple(chains)


def i1_violet_chains() -> Grammar:
    """Covalent polymer gel with literal entanglement and fracture chemistry."""
    chains = _wormlike_chains()
    backbone = _mask()
    core = _mask()
    crystalline = _mask()
    crosslinks = _mask()
    knots = _mask()
    pendants = _mask()
    loops = _mask()
    gaps = _mask()
    caps = _mask()

    for chain_index, points in enumerate(chains):
        _stroke(backbone, points, 5 if chain_index % 3 else 6)
        _stroke(core, points, 2)

        # Crystalline stretches are selected by local persistence, not texture.
        for j in range(16 + chain_index % 7, len(points) - 17, 43):
            before, centre, after = points[j - 8], points[j], points[j + 8]
            v0, v1 = centre - before, after - centre
            alignment = float(np.dot(v0, v1) / (np.linalg.norm(v0) * np.linalg.norm(v1) + 1e-6))
            if alignment > .84:
                tangent = after - before
                tangent /= np.linalg.norm(tangent) + 1e-6
                normal = np.asarray((-tangent[1], tangent[0]), np.float32)
                _line(crystalline, before + 2.4 * normal, after + 2.4 * normal, 2)
                _line(crystalline, before - 2.4 * normal, after - 2.4 * normal, 2)

        # Pendant chemistry grows from the local molecular normal.
        for j in range(31 + 3 * (chain_index % 5), len(points) - 8, 71):
            tangent = points[j + 5] - points[j - 5]
            tangent /= np.linalg.norm(tangent) + 1e-6
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            handed = -1.0 if (chain_index + j // 71) % 2 else 1.0
            root = points[j]
            elbow = root + handed * normal * (6.0 + chain_index % 4)
            tip = elbow + tangent * (4.0 + (j // 71) % 4)
            _line(pendants, root, elbow, 2)
            _line(pendants, elbow, tip, 2)
            _circle(pendants, tip, 2.5 + (chain_index % 2), -1)

        # A few true cyclic splice loops attach to, rather than stamp over, chains.
        if chain_index % 3 == 1:
            j = 112 + 13 * (chain_index % 6)
            tangent = points[j + 5] - points[j - 5]
            angle = np.degrees(np.arctan2(tangent[1], tangent[0]))
            _ellipse(loops, points[j], (8 + chain_index % 3, 5), angle, 2)
            _line(loops, points[j - 5], points[j] - .35 * tangent, 2)

        # Radical scission erases a short backbone interval and exposes two caps.
        if chain_index % 4 != 2:
            j = 256 + 7 * (chain_index % 8)
            tangent = points[j + 4] - points[j - 4]
            tangent /= np.linalg.norm(tangent) + 1e-6
            _circle(gaps, points[j], 5.4, -1)
            _circle(caps, points[j] - 5.8 * tangent, 3.0, -1)
            _circle(caps, points[j] + 5.8 * tangent, 3.0, -1)

    # Crosslinks are chemical proximity events between different molecules.
    samples = []
    for ci, points in enumerate(chains):
        for pi in range(22 + ci % 9, len(points) - 20, 23):
            samples.append((ci, pi, points[pi]))
    used = set()
    accepted = 0
    for left, (ci, pi, point) in enumerate(samples):
        best = None
        for right in range(left + 1, len(samples)):
            cj, pj, other = samples[right]
            if ci == cj or (cj, pj) in used:
                continue
            distance = float(np.linalg.norm(other - point))
            if 8.0 < distance < 23.0 and (best is None or distance < best[0]):
                best = (distance, cj, pj, other)
        if best is None:
            continue
        distance, cj, pj, other = best
        signature = (ci * 37 + cj * 23 + pi * 7 + pj * 3) % 17
        if signature not in (0, 3, 7, 11):
            continue
        _line(crosslinks, point, other, 2)
        midpoint = (point + other) * .5
        _circle(crosslinks, midpoint, 2.2, -1)
        if accepted % 4 == 1:
            # The later chain crosses over with its own sheath/core restored.
            tangent = chains[cj][min(pj + 5, len(chains[cj]) - 1)] - chains[cj][max(pj - 5, 0)]
            tangent /= np.linalg.norm(tangent) + 1e-6
            _line(knots, midpoint - 7.0 * tangent, midpoint + 7.0 * tangent, 7)
            _line(core, midpoint - 7.0 * tangent, midpoint + 7.0 * tangent, 2)
        used.add((ci, pi))
        used.add((cj, pj))
        accepted += 1
        if accepted >= 92:
            break

    backbone = _f(backbone)
    core = _f(core * (1.0 - _dilate(gaps, 1)))
    backbone = _f(backbone * (1.0 - gaps))
    strain = _f(_halo(backbone, 4.2) * (1.0 - _dilate(backbone, 1)))

    masks = {
        "strain_sheaths": strain,
        "covalent_backbones": backbone,
        "conjugated_pi_cores": core,
        "crystalline_stretches": crystalline,
        "disulfide_crosslinks": crosslinks,
        "knot_overpasses": knots,
        "pendant_sidegroups": pendants,
        "cyclic_splices": loops,
        "radical_scission_gaps": gaps,
        "oxidised_break_caps": caps,
    }
    banks = {
        "strain_sheaths": "A",
        "covalent_backbones": "A",
        "conjugated_pi_cores": "B",
        "crystalline_stretches": "A",
        "disulfide_crosslinks": "B",
        "knot_overpasses": "A",
        "pendant_sidegroups": "B",
        "cyclic_splices": "B",
        "radical_scission_gaps": "N",
        "oxidised_break_caps": "B",
    }

    # Literal Violet Chains paint recipe.  It is intentionally not a shared
    # field-to-palette compositor: each chemical family owns its own pigments.
    paint = np.broadcast_to(_rgb("#090713"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#231044"), .76 * strain)
    paint = _blend(paint, _rgb("#7228ad"), .91 * backbone)
    paint = _blend(paint, _rgb("#e2c7ff"), .94 * crystalline)
    paint = _blend(paint, _rgb("#24d8ea"), .96 * core)
    paint = _blend(paint, _rgb("#ffbd27"), .93 * crosslinks)
    paint = _blend(paint, _rgb("#ff4ed8"), .91 * pendants)
    paint = _blend(paint, _rgb("#70f4a0"), .94 * loops)
    paint = _blend(paint, _rgb("#090713"), .98 * gaps)
    paint = _blend(paint, _rgb("#ff7a35"), .97 * caps)
    paint = _blend(paint, _rgb("#f5edff"), .97 * knots)
    paint = _blend(paint, _rgb("#3af3ff"), .94 * core)

    # Hue-null preserves the same chemistry in ordered luminance tiers.
    hue_null = np.full((S, S), .035, np.float32)
    for name, level in (
        ("strain_sheaths", .16), ("covalent_backbones", .39),
        ("crystalline_stretches", .89), ("conjugated_pi_cores", .68),
        ("disulfide_crosslinks", .92), ("pendant_sidegroups", .58),
        ("cyclic_splices", .77), ("radical_scission_gaps", .025),
        ("oxidised_break_caps", .84), ("knot_overpasses", .97),
    ):
        hue_null = hue_null * (1.0 - masks[name]) + level * masks[name]
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    # M/R/Cc tell three different material stories from literal masks.
    metal = _write_channel(7, masks, (
        ("strain_sheaths", 52), ("covalent_backbones", 166),
        ("conjugated_pi_cores", 238), ("crystalline_stretches", 252),
        ("disulfide_crosslinks", 208), ("pendant_sidegroups", 118),
        ("cyclic_splices", 188), ("radical_scission_gaps", 3),
        ("oxidised_break_caps", 232), ("knot_overpasses", 248),
    ))
    rough = _write_channel(242, masks, (
        ("strain_sheaths", 205), ("covalent_backbones", 96),
        ("conjugated_pi_cores", 34), ("crystalline_stretches", 55),
        ("disulfide_crosslinks", 126), ("pendant_sidegroups", 172),
        ("cyclic_splices", 111), ("radical_scission_gaps", 252),
        ("oxidised_break_caps", 67), ("knot_overpasses", 43),
    ))
    coat = _write_channel(5, masks, (
        ("strain_sheaths", 58), ("covalent_backbones", 152),
        ("conjugated_pi_cores", 218), ("crystalline_stretches", 238),
        ("disulfide_crosslinks", 250), ("pendant_sidegroups", 132),
        ("cyclic_splices", 226), ("radical_scission_gaps", 2),
        ("oxidised_break_caps", 246), ("knot_overpasses", 254),
    ))

    marks = tuple((name, _f(mask), banks[name]) for name, mask in masks.items())
    if any(float(mask.std()) < .0015 for _name, mask, _owner in marks):
        raise ValueError("I1 Violet Chains has a visually flat causal family")
    spec = tuple(np.clip(ch, 0, 255).astype(np.float32)
                 for ch in (metal, rough, coat))
    return Grammar(marks, _f(paint), _f(hue_null), spec)


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fpe_violet_chains": i1_violet_chains,
}
HUES = {"fpe_violet_chains": (.77, .30)}
PETRI_IDS = tuple(BUILDERS)


@lru_cache(maxsize=20)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    spec = np.stack(grammar.explicit_spec, axis=2)
    return grammar.paint, np.clip(spec, 0, 255).astype(np.uint8)


def clear_cache():
    _authored.cache_clear()


def debug_grammar(fid: str) -> Grammar:
    return BUILDERS[fid]()


def debug_hue_null(fid: str):
    return debug_grammar(fid).hue_null


def owner_unions(grammar: Grammar):
    unions = {key: np.zeros((S, S), np.float32) for key in ("A", "B", "N")}
    for _name, mask, owner in grammar.marks:
        unions[owner] = np.maximum(unions[owner], mask)
    return unions


def debug_angle_pair(fid: str):
    paint, spec = _authored(fid)
    owners = owner_unions(debug_grammar(fid))
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - .50 * rough, .22, 1.0)
    light_a = np.clip(.09 + 1.10 * metal * aperture + .35 * owners["A"]
                      - .09 * owners["B"], .08, 1.28)
    light_b = np.clip(.09 + 1.10 * coat * aperture + .35 * owners["B"]
                      - .09 * owners["A"], .08, 1.28)
    warm = np.asarray((.25, .065, .008), np.float32)
    cool = np.asarray((.006, .10, .27), np.float32)
    angle_a = np.clip(paint * light_a[..., None]
                      + warm * (metal * aperture * (.42 + .58 * owners["A"]))[..., None], 0, 1)
    angle_b = np.clip(paint * light_b[..., None]
                      + cool * (coat * aperture * (.42 + .58 * owners["B"]))[..., None], 0, 1)
    return angle_a.astype(np.float32), angle_b.astype(np.float32), np.abs(angle_a - angle_b).astype(np.float32)


__all__ = ["BUILDERS", "Grammar", "HUES", "PETRI_IDS", "_authored",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "owner_unions"]
