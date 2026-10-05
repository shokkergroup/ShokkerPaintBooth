# -*- coding: utf-8 -*-
"""Petri VC-I1: one recursive space-filling polymer.

The dominant carrier is a single order-six Hilbert backbone, analytically
softened and chemically segmented—not a random walk, spaghetti cloud, repeated
chain stamp, row/grid texture, or shared scalar field.  Sequence-distant
contacts create real crosslinks and overpasses; curvature creates strain and
pi-bond anatomy; deterministic scissions create caps, collars and repair
splices.  Every visible mark descends from the one persistent polymer.

SPB-WILDS VC-I1, tick 1, 2026-08-24.  Isolated and unwired.  This is candidate
evidence only; metrics/hashes do not claim owner acceptance.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import cv2
import numpy as np

from .fractured_wilds_morpho_bio_independent_w1_2026 import (
    CALM_SPEC, Grammar, S, _blend, _circle, _f, _line, _rgb, _write_channel,
)


def _hilbert_xy(order: int):
    """Return integer Hilbert coordinates in sequence order."""
    n = 1 << int(order)

    def rotate(scale, x, y, rx, ry):
        if ry == 0:
            if rx == 1:
                x = scale - 1 - x
                y = scale - 1 - y
            x, y = y, x
        return x, y

    points = []
    for distance in range(n * n):
        t = int(distance)
        x = y = 0
        scale = 1
        while scale < n:
            rx = 1 & (t // 2)
            ry = 1 & (t ^ rx)
            x, y = rotate(scale, x, y, rx, ry)
            x += scale * rx
            y += scale * ry
            t //= 4
            scale *= 2
        points.append((x, y))
    return np.asarray(points, np.float32)


def _polymer_entanglement() -> Grammar:
    grid = _hilbert_xy(6)
    n = 64
    margin = 4.0
    step = (S - 2.0 * margin) / float(n - 1)
    pts = margin + grid * step

    # A bounded analytic displacement softens the rectilinear recursion while
    # retaining exact sequence identity.  It is geometry, never paint noise.
    phase = np.arange(len(pts), dtype=np.float32)
    pts[:, 0] += (1.05 * np.sin(.019 * phase)
                  + .65 * np.sin(.071 * phase + .6))
    pts[:, 1] += (.92 * np.cos(.023 * phase + .4)
                  + .58 * np.sin(.061 * phase - .2))
    pts = np.clip(pts, 2.0, S - 3.0)

    sheath = np.zeros((S, S), np.float32)
    backbone_a = np.zeros_like(sheath)
    backbone_b = np.zeros_like(sheath)
    pi_cores = np.zeros_like(sheath)
    kink_folds = np.zeros_like(sheath)
    crosslinks = np.zeros_like(sheath)
    overpass_lips = np.zeros_like(sheath)
    sidegroups = np.zeros_like(sheath)
    cyclic_splices = np.zeros_like(sheath)
    scission_voids = np.zeros_like(sheath)
    oxidized_caps = np.zeros_like(sheath)
    state_collars = np.zeros_like(sheath)

    strengths = (.30, .39, .48, .57, .66, .75, .86, .98)
    gap_segments = set()
    for start in range(137, len(pts) - 3, 181):
        length = 1 + ((start // 181) % 2)
        gap_segments.update(range(start, min(start + length, len(pts) - 1)))

    # Curvature and sequence chemistry control anatomy.  The A/B state changes
    # in unequal prime-length runs so there is no checkerboard cadence.
    previous_state = None
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        tier = (i * 5 + (i // 17) * 3 + (i // 61)) % 8
        strength = strengths[tier]
        if i in gap_segments:
            _line(scission_voids, a, b, 7, .94)
            _circle(oxidized_caps, a, 2.2, .62 + .35 * strength)
            _circle(oxidized_caps, b, 2.2, .62 + .35 * strength)
            continue

        state = ((i // 19) + (i // 47) + (i // 113)) & 1
        _line(sheath, a, b, 7, .28 + .49 * strength)
        _line(backbone_a if state == 0 else backbone_b,
              a, b, 4, .44 + .53 * strength)
        if (i % 5) in (0, 1, 3):
            _line(pi_cores, a, b, 2, .36 + .61 * strength)

        if previous_state is not None and state != previous_state:
            _circle(state_collars, a, 3.3, .47 + .49 * strength)
        previous_state = state

        if 0 < i < len(pts) - 2:
            incoming = pts[i] - pts[i - 1]
            outgoing = pts[i + 1] - pts[i]
            denom = (float(np.linalg.norm(incoming) * np.linalg.norm(outgoing)) + 1e-6)
            turn = 1.0 - float(np.dot(incoming, outgoing) / denom)
            if turn > .36:
                _circle(kink_folds, a, 3.0, np.clip(.31 + .48 * turn, 0, .98))

        # Attached side chemistry appears only on selected backbone segments.
        if i % 149 == 37:
            tangent = b - a
            tangent /= float(np.linalg.norm(tangent)) + 1e-6
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            root = .5 * (a + b)
            tip = root + normal * (4.1 + (i % 3))
            _line(sidegroups, root, tip, 2, .66 + .26 * strength)
            _line(sidegroups, tip, tip + tangent * 2.2, 2, .48 + .37 * strength)

    # Sequence-distant Hilbert cells often become spatial neighbours.  Those
    # exact contacts, not scatter, create a bounded set of true crosslinks.
    lookup = {tuple(map(int, xy)): idx for idx, xy in enumerate(grid)}
    linked = set()
    for i in range(31, len(grid) - 31, 23):
        gx, gy = map(int, grid[i])
        for dx, dy in ((2, 0), (0, 2), (-2, 0), (0, -2)):
            j = lookup.get((gx + dx, gy + dy))
            if j is None or abs(j - i) < 80:
                continue
            pair = tuple(sorted((i, j)))
            if pair in linked or len(linked) >= 92:
                continue
            linked.add(pair)
            a, b = pts[i], pts[j]
            mid = .5 * (a + b)
            strength = strengths[(i + j) % 8]
            _line(overpass_lips, a, b, 6, .31 + .51 * strength)
            _line(crosslinks, a, b, 3, .48 + .49 * strength)
            _circle(overpass_lips, mid, 2.4, .54 + .39 * strength)
            break

    # Rare cyclic repair splices are attached to high-curvature sites and vary
    # in aspect/direction.  They cannot become a repeated ring field.
    for slot, i in enumerate(range(211, len(pts) - 60, 467)):
        center = tuple(np.rint(pts[i]).astype(int))
        axes = (3 + (slot % 3), 2 + ((slot + 1) % 2))
        angle = float((slot * 47 + i * 3) % 180)
        cv2.ellipse(cyclic_splices, center, axes, angle, 28, 322,
                    .62 + .04 * (slot % 8), 2, cv2.LINE_AA)
        _line(cyclic_splices, pts[i], pts[i] + np.asarray((2.4, -1.8)),
              2, .72)

    # Remove the authored scissions from every continuous backbone layer.
    keep = 1.0 - _f(scission_voids)
    sheath *= keep
    backbone_a *= keep
    backbone_b *= keep
    pi_cores *= keep
    kink_folds *= keep

    masks = {
        "persistent_strain_sheath": _f(sheath),
        "metallic_backbone_a": _f(backbone_a),
        "clearcoat_backbone_b": _f(backbone_b),
        "pi_bond_cores": _f(pi_cores),
        "curvature_kink_folds": _f(kink_folds),
        "sequence_distant_crosslinks": _f(crosslinks),
        "overpass_strain_lips": _f(overpass_lips),
        "attached_sidegroups": _f(sidegroups),
        "cyclic_repair_splices": _f(cyclic_splices),
        "scission_voids": _f(scission_voids),
        "oxidized_scission_caps": _f(oxidized_caps),
        "chemistry_state_collars": _f(state_collars),
    }
    banks = {
        "persistent_strain_sheath": "N",
        "metallic_backbone_a": "A", "pi_bond_cores": "A",
        "curvature_kink_folds": "A", "attached_sidegroups": "A",
        "clearcoat_backbone_b": "B", "sequence_distant_crosslinks": "B",
        "overpass_strain_lips": "B", "cyclic_repair_splices": "B",
        "scission_voids": "N", "oxidized_scission_caps": "B",
        "chemistry_state_collars": "A",
    }

    paint = np.empty((S, S, 3), np.float32)
    paint[:] = _rgb("#05030d")
    paint = _blend(paint, _rgb("#31104d"), .70 * masks["persistent_strain_sheath"])
    paint = _blend(paint, _rgb("#ff2fd1"), .96 * masks["metallic_backbone_a"])
    paint = _blend(paint, _rgb("#5a29ff"), .97 * masks["clearcoat_backbone_b"])
    paint = _blend(paint, _rgb("#ffd94a"), .98 * masks["pi_bond_cores"])
    paint = _blend(paint, _rgb("#ff6b3d"), .94 * masks["curvature_kink_folds"])
    paint = _blend(paint, _rgb("#17eaff"), .98 * masks["sequence_distant_crosslinks"])
    paint = _blend(paint, _rgb("#6effcf"), .93 * masks["overpass_strain_lips"])
    paint = _blend(paint, _rgb("#ff87ed"), .94 * masks["attached_sidegroups"])
    paint = _blend(paint, _rgb("#b5ff5e"), .94 * masks["cyclic_repair_splices"])
    paint = _blend(paint, _rgb("#020106"), .99 * masks["scission_voids"])
    paint = _blend(paint, _rgb("#fff2c2"), .98 * masks["oxidized_scission_caps"])
    paint = _blend(paint, _rgb("#ff356c"), .94 * masks["chemistry_state_collars"])

    hue_null = np.full((S, S), .025, np.float32)
    levels = (.23, .76, .45, .96, .60, .84, .37, .70, .90, .05, .99, .53)
    for (name, mask), level in zip(masks.items(), levels):
        hue_null = hue_null * (1.0 - mask) + float(level) * mask
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    metal = _write_channel(6, masks, (
        ("persistent_strain_sheath", 92), ("metallic_backbone_a", 238),
        ("pi_bond_cores", 254), ("curvature_kink_folds", 202),
        ("chemistry_state_collars", 174), ("attached_sidegroups", 146),
        ("clearcoat_backbone_b", 56), ("sequence_distant_crosslinks", 128),
        ("overpass_strain_lips", 218), ("cyclic_repair_splices", 188),
        ("scission_voids", 4), ("oxidized_scission_caps", 112),
    ))
    rough = _write_channel(246, masks, (
        ("persistent_strain_sheath", 178), ("metallic_backbone_a", 62),
        ("pi_bond_cores", 24), ("curvature_kink_folds", 118),
        ("chemistry_state_collars", 92), ("attached_sidegroups", 154),
        ("clearcoat_backbone_b", 204), ("sequence_distant_crosslinks", 76),
        ("overpass_strain_lips", 48), ("cyclic_repair_splices", 132),
        ("scission_voids", 252), ("oxidized_scission_caps", 222),
    ))
    coat = _write_channel(9, masks, (
        ("persistent_strain_sheath", 62), ("clearcoat_backbone_b", 242),
        ("sequence_distant_crosslinks", 252), ("overpass_strain_lips", 206),
        ("cyclic_repair_splices", 178), ("oxidized_scission_caps", 224),
        ("metallic_backbone_a", 42), ("pi_bond_cores", 116),
        ("curvature_kink_folds", 84), ("chemistry_state_collars", 138),
        ("attached_sidegroups", 164), ("scission_voids", 5),
    ))

    marks = tuple((name, mask, banks[name]) for name, mask in masks.items())
    if any(float(mask.std()) < .0015 for _name, mask, _bank in marks):
        raise ValueError("VC-I1 contains a visually flat semantic family")
    return Grammar(marks, _f(paint), _f(hue_null), (metal, rough, coat))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fpe_violet_chains": _polymer_entanglement,
}
PETRI_IDS = tuple(BUILDERS)
HUES = {"fpe_violet_chains": (.91, .60)}


@lru_cache(maxsize=2)
def _authored(fid):
    grammar = BUILDERS[fid]()
    spec = np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)
    return grammar.paint, spec


def clear_cache():
    _authored.cache_clear()


def debug_grammar(fid):
    return BUILDERS[fid]()


def debug_hue_null(fid):
    return debug_grammar(fid).hue_null


def owner_unions(grammar):
    unions = {key: np.zeros((S, S), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        unions[bank] = np.maximum(unions[bank], mask)
    return unions


def debug_angle_pair(fid):
    paint, spec = _authored(fid)
    owners = owner_unions(debug_grammar(fid))
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - .54 * rough, .20, 1.0)
    light_a = np.clip(.08 + 1.08 * metal * aperture
                      + .32 * owners["A"] - .11 * owners["B"], .07, 1.30)
    light_b = np.clip(.08 + 1.08 * coat * aperture
                      + .32 * owners["B"] - .11 * owners["A"], .07, 1.30)
    angle_a = np.clip(paint * light_a[..., None]
                      + np.asarray((.31, .085, .005), np.float32)
                      * (metal * aperture * owners["A"])[..., None], 0, 1)
    angle_b = np.clip(paint * light_b[..., None]
                      + np.asarray((.025, .09, .34), np.float32)
                      * (coat * aperture * owners["B"])[..., None], 0, 1)
    return (angle_a.astype(np.float32), angle_b.astype(np.float32),
            np.abs(angle_a - angle_b).astype(np.float32))


def _entry(fid):
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
        authored, _spec = _authored(fid)
        authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_NEAREST)
        alpha = np.clip(zone * max(0.0, float(pm)), 0, 1)[..., None]
        return np.clip(source * (1.0 - alpha) + authored * alpha, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        h, w = int(shape[0]), int(shape[1])
        zone = np.asarray(mask, np.float32)
        if zone.ndim == 3:
            zone = zone[:, :, 0]
        if zone.shape != (h, w):
            zone = cv2.resize(zone, (w, h), interpolation=cv2.INTER_LINEAR)
        _paint, authored = _authored(fid)
        authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        active = np.clip(CALM_SPEC + (authored - CALM_SPEC)
                         * max(0.0, float(sm)), 0, 255)
        alpha = np.clip(zone, 0, 1)[..., None]
        out = np.empty((h, w, 4), np.uint8)
        out[:, :, :3] = np.clip(active * alpha + CALM_SPEC * (1.0 - alpha),
                                0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return out
    return spec_fn, paint_fn


def install_into_engine(registry, base_registry=None):
    for fid in PETRI_IDS:
        registry[fid] = _entry(fid)
    return "fractured-wilds-petri-violet-chains-vc-i1: 1 isolated candidate"


__all__ = ["BUILDERS", "PETRI_IDS", "HUES", "_authored", "_entry",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "install_into_engine", "owner_unions"]
