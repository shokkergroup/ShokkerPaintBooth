# -*- coding: utf-8 -*-
"""Bloom independent LV-I1: full-crop botanical liana drape.

W4 Leafvine was a recognizable but sparse right-heavy branch clump.  LV-I1
replaces that silhouette with many edge-to-edge, mutually crossing lianas whose
filled serrated leaves carry the image.  Stems, axillary nodes, over/under lips,
tendril wraps, thorns, pods, midribs and tributaries remain attached to their
own vines.  There is no RNG, noise texture, repeated icon sheet, regular
trellis, or shared spec substrate.

SPB-WILDS LV-I1, tick 1, 2026-08-24.  Candidate only, isolated and unwired.
Reject if it reads first as rails, a branch graph, or repeated leaf stamps.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import cv2
import numpy as np

from .fractured_wilds_morpho_bio_independent_w1_2026 import (
    CALM_SPEC, Grammar, S, _blend, _circle, _f, _line, _mask, _poly, _rgb,
    _write_channel,
)


def _bezier(p0, p1, p2, p3, count=148):
    t = np.linspace(0.0, 1.0, int(count), dtype=np.float32)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, np.float32) for p in (p0, p1, p2, p3))
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


def _curve(target, points, width, value):
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(target, [pts], False, float(value), int(width), cv2.LINE_AA)


def _leaf_polygon(base, tangent, normal, length, width, phase):
    """One asymmetric serrated blade built around a short curved midline."""
    rows = []
    for i, u in enumerate(np.linspace(0.0, 1.0, 9, dtype=np.float32)):
        centre = (base + normal * (length * u)
                  + tangent * (1.2 * np.sin(np.pi * u + phase)))
        envelope = width * (max(float(np.sin(np.pi * u)), 0.0) ** .72)
        serration = 1.0 + .22 * (-1.0 if i & 1 else 1.0)
        rows.append((centre, envelope * serration))
    left = [centre - tangent * spread for centre, spread in rows]
    right = [centre + tangent * spread for centre, spread in rows[::-1]]
    return np.asarray(left + right, np.float32), np.asarray([r[0] for r in rows])


def _liana_drape() -> Grammar:
    woody_stems = _mask()
    live_stems = _mask()
    mature_leaves = _mask()
    young_leaves = _mask()
    serrated_margins = _mask()
    blade_ribs = _mask()
    tendril_wraps = _mask()
    thorn_tips = _mask()
    seed_pods = _mask()
    axillary_nodes = _mask()
    over_under_lips = _mask()

    paths = []
    # Four unrelated edge-crossing families create a drape without a grid.
    # Every path has unique controls and unequal curvature; no shared focus.
    for i in range(36):
        family = i % 4
        q = (21.0 + i * 47.3 + 17.0 * np.sin(i * 1.37)) % S
        r = (38.0 + i * 71.9 + 13.0 * np.cos(i * .91)) % S
        bow = 42.0 * np.sin(i * 1.17) + 19.0 * np.sin(i * .43)
        if family == 0:
            p0, p3 = (-8.0, q), (S + 8.0, r)
            p1, p2 = (128.0, q + bow), (382.0, r - .72 * bow)
        elif family == 1:
            p0, p3 = (q, -8.0), (r, S + 8.0)
            p1, p2 = (q - .63 * bow, 132.0), (r + bow, 386.0)
        elif family == 2:
            p0, p3 = (-8.0, q), (r, S + 8.0)
            p1, p2 = (112.0, q - bow), (r + .76 * bow, 374.0)
        else:
            p0, p3 = (S + 8.0, q), (r, -8.0)
            p1, p2 = (396.0, q + .58 * bow), (r - bow, 116.0)
        path = _bezier(p0, p1, p2, p3)
        paths.append(path)
        strength = (.28, .38, .48, .58, .68, .78, .88, .98)[(i * 5) % 8]
        target = woody_stems if i % 5 in (0, 1) else live_stems
        _curve(target, path, 2 + (i % 11 == 0), .42 + .54 * strength)

        tangent = np.gradient(path, axis=0)
        tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1.0e-6
        normal = np.c_[-tangent[:, 1], tangent[:, 0]]

        # Unequal cadence comes from vine ancestry, not jitter.  Leaves are
        # filled and visually dominant; stems are only their causal support.
        cadence = 6 + (i * 3) % 5
        for leaf_i, k in enumerate(range(9 + i % 7, len(path) - 8, cadence)):
            if (leaf_i + i * 2) % 9 == 0:
                continue
            side = -1.0 if (leaf_i + i) & 1 else 1.0
            base = path[k]
            t = tangent[k]
            n = normal[k] * side
            length = 5.1 + .48 * ((leaf_i * 3 + i) % 6)
            width = 2.0 + .31 * ((leaf_i + i * 2) % 5)
            blade, midline = _leaf_polygon(base, t, n, length, width,
                                           .37 * i + .61 * leaf_i)
            blade_target = mature_leaves if (i + leaf_i) % 5 in (0, 1, 2) else young_leaves
            level = (.30, .40, .50, .60, .70, .80, .90, .98)[
                (i * 7 + leaf_i * 3) % 8]
            _poly(blade_target, blade, .36 + .58 * level)
            _curve(blade_ribs, midline, 2, .42 + .52 * level)
            for rib_i in (2, 4, 6):
                centre = midline[rib_i]
                edge = blade[rib_i] if (rib_i + leaf_i) % 2 else blade[-rib_i - 1]
                _line(blade_ribs, centre, edge, 1, .38 + .50 * level)
            for a, b in zip(blade, np.roll(blade, -1, axis=0)):
                if int(np.linalg.norm(b - a)) <= 5:
                    _line(serrated_margins, a, b, 1, .44 + .50 * level)

            # Axillary anatomy appears at the same causal attachment point.
            if (leaf_i + 3 * i) % 7 == 0:
                _circle(axillary_nodes, base, 1.25 + .18 * (leaf_i % 3),
                        .54 + .40 * level)
            if (leaf_i + i) % 13 == 0:
                tip = base - n * (3.0 + .45 * (leaf_i % 4)) + t * 1.5
                _line(thorn_tips, base, tip, 2, .54 + .40 * level)
            if (leaf_i + 2 * i) % 17 == 0:
                pod_center = base + n * 4.1 + t * 2.0
                cv2.ellipse(seed_pods, tuple(np.rint(pod_center).astype(int)),
                            (2 + leaf_i % 2, 4),
                            float(np.degrees(np.arctan2(n[1], n[0]))),
                            0, 360, float(.48 + .46 * level), -1, cv2.LINE_AA)
                _line(blade_ribs, base, pod_center, 1, .46 + .46 * level)
            if (leaf_i + i * 5) % 19 == 0:
                hook_center = base - n * 3.0
                cv2.ellipse(tendril_wraps,
                            tuple(np.rint(hook_center).astype(int)),
                            (3 + leaf_i % 3, 2 + i % 2),
                            float(np.degrees(np.arctan2(t[1], t[0]))),
                            22, 302, float(.50 + .44 * level), 2, cv2.LINE_AA)

    # Crossings are derived from old/live overlap.  The small deletion plus lip
    # makes an over/under event rather than allowing a generic blended graph.
    old_near = cv2.dilate((woody_stems > .2).astype(np.uint8),
                          np.ones((5, 5), np.uint8))
    live_near = cv2.dilate((live_stems > .2).astype(np.uint8),
                           np.ones((5, 5), np.uint8))
    crossings = (old_near & live_near).astype(np.float32)
    over_under_lips[:] = _f(cv2.dilate(crossings, np.ones((3, 3), np.uint8))
                            - crossings)

    masks = {
        "woody_cambium_lianas": _f(woody_stems),
        "live_climbing_stems": _f(live_stems),
        "mature_serrated_leaf_blades": _f(mature_leaves),
        "young_serrated_leaf_blades": _f(young_leaves),
        "attached_serrated_margins": _f(serrated_margins),
        "leaf_midribs_and_tributaries": _f(blade_ribs),
        "axillary_tendril_wraps": _f(tendril_wraps),
        "causal_thorn_tips": _f(thorn_tips),
        "attached_seed_pods": _f(seed_pods),
        "axillary_growth_nodes": _f(axillary_nodes),
        "over_under_crossing_lips": _f(over_under_lips),
    }
    banks = {
        "woody_cambium_lianas": "A", "live_climbing_stems": "B",
        "mature_serrated_leaf_blades": "A",
        "young_serrated_leaf_blades": "B",
        "attached_serrated_margins": "A",
        "leaf_midribs_and_tributaries": "B",
        "axillary_tendril_wraps": "B", "causal_thorn_tips": "A",
        "attached_seed_pods": "A", "axillary_growth_nodes": "N",
        "over_under_crossing_lips": "N",
    }

    paint = np.broadcast_to(_rgb("#050b0a"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#6c2815"), .62 * masks["woody_cambium_lianas"])
    paint = _blend(paint, _rgb("#15685b"), .60 * masks["live_climbing_stems"])
    paint = _blend(paint, _rgb("#ef3b91"), .94 * masks["mature_serrated_leaf_blades"])
    paint = _blend(paint, _rgb("#42ec68"), .95 * masks["young_serrated_leaf_blades"])
    paint = _blend(paint, _rgb("#ffb52e"), .94 * masks["attached_serrated_margins"])
    paint = _blend(paint, _rgb("#23e7ff"), .95 * masks["leaf_midribs_and_tributaries"])
    paint = _blend(paint, _rgb("#a84dff"), .96 * masks["axillary_tendril_wraps"])
    paint = _blend(paint, _rgb("#fff0a5"), .97 * masks["causal_thorn_tips"])
    paint = _blend(paint, _rgb("#ff6b24"), .96 * masks["attached_seed_pods"])
    paint = _blend(paint, _rgb("#f6ffff"), .98 * masks["axillary_growth_nodes"])
    paint = _blend(paint, _rgb("#12182d"), .94 * masks["over_under_crossing_lips"])

    hue_null = np.full((S, S), .025, np.float32)
    levels = (.30, .53, .72, .42, .92, .81, .63, .98, .76, .88, .12)
    for (name, mask), level in zip(masks.items(), levels):
        hue_null = hue_null * (1.0 - mask) + level * mask
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    metal = _write_channel(5, masks, (
        ("mature_serrated_leaf_blades", 224), ("attached_serrated_margins", 252),
        ("woody_cambium_lianas", 184), ("causal_thorn_tips", 206),
        ("attached_seed_pods", 148), ("axillary_growth_nodes", 118),
        ("live_climbing_stems", 24), ("young_serrated_leaf_blades", 52),
        ("leaf_midribs_and_tributaries", 78), ("axillary_tendril_wraps", 96),
        ("over_under_crossing_lips", 38),
    ))
    rough = _write_channel(244, masks, (
        ("mature_serrated_leaf_blades", 54), ("attached_serrated_margins", 24),
        ("woody_cambium_lianas", 94), ("causal_thorn_tips", 38),
        ("attached_seed_pods", 126), ("axillary_growth_nodes", 174),
        ("live_climbing_stems", 216), ("young_serrated_leaf_blades", 188),
        ("leaf_midribs_and_tributaries", 152), ("axillary_tendril_wraps", 112),
        ("over_under_crossing_lips", 232),
    ))
    coat = _write_channel(6, masks, (
        ("mature_serrated_leaf_blades", 38), ("attached_serrated_margins", 64),
        ("woody_cambium_lianas", 18), ("causal_thorn_tips", 92),
        ("attached_seed_pods", 124), ("axillary_growth_nodes", 152),
        ("live_climbing_stems", 214), ("young_serrated_leaf_blades", 252),
        ("leaf_midribs_and_tributaries", 232), ("axillary_tendril_wraps", 188),
        ("over_under_crossing_lips", 22),
    ))

    marks = tuple((name, mask, banks[name]) for name, mask in masks.items())
    if any(float(mask.std()) < .0015 for _name, mask, _bank in marks):
        raise ValueError("LV-I1 contains a visually flat semantic family")
    return Grammar(marks, _f(paint), _f(hue_null), (metal, rough, coat))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fbl_leafvine_drape": _liana_drape,
}
HUES = {"fbl_leafvine_drape": (.92, .34)}
BLOOM_IDS = tuple(BUILDERS)


@lru_cache(maxsize=2)
def _authored(fid):
    grammar = BUILDERS[fid]()
    return grammar.paint, np.clip(np.stack(grammar.explicit_spec, axis=2),
                                  0, 255).astype(np.uint8)


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
    la = np.clip(.08 + 1.08 * metal * aperture + .34 * owners["A"]
                 - .12 * owners["B"], .07, 1.31)
    lb = np.clip(.08 + 1.08 * coat * aperture + .34 * owners["B"]
                 - .12 * owners["A"], .07, 1.31)
    a = np.clip(paint * la[..., None]
                + np.asarray((.34, .025, .12), np.float32)
                * (metal * aperture * owners["A"])[..., None], 0, 1)
    b = np.clip(paint * lb[..., None]
                + np.asarray((.02, .29, .14), np.float32)
                * (coat * aperture * owners["B"])[..., None], 0, 1)
    return a.astype(np.float32), b.astype(np.float32), np.abs(a - b).astype(np.float32)


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
    for fid in BLOOM_IDS:
        registry[fid] = _entry(fid)
    return "fractured-wilds-bloom-leafvine-lv-i1: 1 isolated candidate"


__all__ = ["BUILDERS", "BLOOM_IDS", "HUES", "_authored", "_entry",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "install_into_engine", "owner_unions"]
