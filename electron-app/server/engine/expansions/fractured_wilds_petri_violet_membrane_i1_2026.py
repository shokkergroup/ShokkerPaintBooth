# -*- coding: utf-8 -*-
"""Petri VM-I1: projected cubic-phase bilayer.

One isolated ``fpe_violet_membrane`` experiment.  The carrier is an analytic,
quasiperiodically bent triply-periodic membrane: two signed bilayer faces,
saddle patches, fusion necks, protein rafts, transmembrane pores, cleavage
tears, vesicle buds, broken lips and healed seams all descend from the same
implicit 3-D surface.  No sampled noise, random field, generic spec overlay,
row/grid placement, or recolor-derived separation enters the construction.

SPB-WILDS VM-I1, tick 1, 2026-08-24.  Owner verdict addressed: visually
identical recolors and identical spec carriers are wasted catalog slots.
Candidate only, isolated and unwired; owner acceptance is not claimed.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import cv2
import numpy as np

from .fractured_wilds_morpho_bio_independent_w1_2026 import (
    CALM_SPEC, Grammar, S, _blend, _f, _rgb, _write_channel,
)


TAU = float(2.0 * np.pi)


def _bump(value, center=0.0, width=1.0):
    value = np.asarray(value, np.float32)
    return np.exp(-np.square((value - float(center)) / float(width))).astype(np.float32)


def _edge(mask, sigma=.55):
    src = cv2.GaussianBlur(np.asarray(mask, np.float32), (0, 0), float(sigma))
    return _f(np.abs(cv2.Laplacian(src, cv2.CV_32F)) * 3.2)


def _cubic_bilayer() -> Grammar:
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    x = xx / float(S)
    y = yy / float(S)

    # Sixty-ish cells across the canvas keep every principal fold within the
    # 8--32 native-pixel doctrine.  The irrational, low-amplitude phase bends
    # destroy periodic registration without becoming a painted noise layer.
    bend = (
        .24 * np.sin(TAU * (np.sqrt(2.0) * 2.3 * x + np.sqrt(3.0) * 1.7 * y))
        + .17 * np.cos(TAU * (np.sqrt(5.0) * 1.1 * x - np.sqrt(2.0) * 2.1 * y))
        + .11 * np.sin(TAU * (3.7 * x + 2.9 * y))
    ).astype(np.float32)
    u = TAU * (61.0 * x + .34 * np.sin(TAU * (1.7 * y + .19 * bend)))
    v = TAU * (53.0 * y + .31 * np.sin(TAU * (1.3 * x - .23 * bend)))
    z = TAU * (.41 * bend + .13 * np.sin(TAU * (2.2 * x - 1.6 * y)))

    # A gyroid-like signed surface and a conjugate Schwarz-like surface.  The
    # latter is never displayed as a free texture: it only identifies actual
    # fusion, pore, and cleavage events on the first membrane.
    g = (np.sin(u) * np.cos(v) + np.sin(v) * np.cos(z)
         + np.sin(z) * np.cos(u)).astype(np.float32)
    q = (np.cos(.93 * u) + np.cos(1.07 * v) + np.cos(z + .31 * np.sin(u - v)))
    q = q.astype(np.float32)

    gy, gx = np.gradient(g)
    grad = np.hypot(gx, gy).astype(np.float32)
    grad_n = _f(grad / (float(np.percentile(grad, 96.0)) + 1e-6))
    lap = cv2.Laplacian(g, cv2.CV_32F)
    lap_n = np.tanh(lap * .38).astype(np.float32)

    face_a = _f(_bump(g, .52, .24) * (.72 + .28 * grad_n))
    face_b = _f(_bump(g, -.52, .24) * (.72 + .28 * grad_n))
    midplane = _f(_bump(g, 0.0, .19))

    # Signed curvature splits the common midplane into two causal materials;
    # this is the Fractured A/B color-flip driver, not a palette-only effect.
    saddle_a = _f(midplane * np.clip(.35 + 1.7 * lap_n, 0, 1))
    saddle_b = _f(midplane * np.clip(.35 - 1.7 * lap_n, 0, 1))

    q_zero = _bump(q, 0.0, .28)
    q_high = _bump(q, 1.38, .25)
    q_low = _bump(q, -1.42, .25)
    fusion_necks = _f(midplane * q_zero * np.clip(1.2 - grad_n, 0, 1))
    transmembrane_pores = _f((face_a + face_b) * q_high * np.clip(.95 - .46 * grad_n, 0, 1))
    vesicle_buds = _f((face_a * q_low + face_b * q_high) * np.clip(.38 + grad_n, 0, 1))

    # Protein rafts are finite patches *on* each signed face.  The local phase
    # changes their length and termination but cannot create an independent
    # stripe/rail carrier away from the membrane.
    local_phase = np.sin(.47 * u - .63 * v + 1.9 * z)
    raft_gate = _bump(local_phase, .34, .23)
    protein_rafts = _f((.58 * face_a + .42 * face_b) * raft_gate)

    cleavage = (np.sin(TAU * (4.7 * x + 3.1 * y) + .72 * bend)
                + .61 * np.sin(TAU * (2.2 * x - 5.3 * y) - .41 * bend))
    cleavage_gate = np.clip((cleavage - .76) * 3.1, 0, 1).astype(np.float32)
    cleavage_tears = _f((face_a + face_b + .55 * midplane) * _edge(cleavage_gate, .7))
    broken_lips = _f((face_a + face_b) * cleavage_gate * (1.0 - .66 * q_zero))

    # Healed seams occupy a different conjugate event than the open tears.
    # They are broad enough to read as material repairs, not random flecks.
    heal_driver = _bump(np.sin(.31 * u + .57 * v - 1.3 * z), -.22, .19)
    healed_seams = _f(midplane * heal_driver * (1.0 - cleavage_gate))
    neck_rims = _f(_edge(fusion_necks, .45) * (face_a + face_b + midplane))

    masks = {
        "positive_bilayer_face": face_a,
        "negative_bilayer_face": face_b,
        "positive_saddle_patch": saddle_a,
        "negative_saddle_patch": saddle_b,
        "fusion_necks": fusion_necks,
        "neck_rims": neck_rims,
        "protein_rafts": protein_rafts,
        "transmembrane_pores": transmembrane_pores,
        "vesicle_buds": vesicle_buds,
        "cleavage_tears": cleavage_tears,
        "broken_membrane_lips": broken_lips,
        "healed_collision_seams": healed_seams,
    }
    banks = {
        "positive_bilayer_face": "A", "positive_saddle_patch": "A",
        "protein_rafts": "A", "vesicle_buds": "A",
        "negative_bilayer_face": "B", "negative_saddle_patch": "B",
        "fusion_necks": "B", "neck_rims": "B",
        "transmembrane_pores": "B", "cleavage_tears": "B",
        "broken_membrane_lips": "N", "healed_collision_seams": "N",
    }

    # Depth is a low-amplitude rendering cue from the same implicit surface;
    # it cannot carry the design when the named semantic masks are removed.
    depth = .5 + .5 * np.tanh(g * .55)
    paint = np.empty((S, S, 3), np.float32)
    paint[:] = _rgb("#09051a")
    paint = _blend(paint, _rgb("#26104d"), .18 * depth)
    paint = _blend(paint, _rgb("#ff2bd5"), .94 * masks["positive_bilayer_face"])
    paint = _blend(paint, _rgb("#7c35ff"), .92 * masks["positive_saddle_patch"])
    paint = _blend(paint, _rgb("#ffb12e"), .96 * masks["protein_rafts"])
    paint = _blend(paint, _rgb("#ff6b72"), .91 * masks["vesicle_buds"])
    paint = _blend(paint, _rgb("#08d9ff"), .95 * masks["negative_bilayer_face"])
    paint = _blend(paint, _rgb("#1641d9"), .93 * masks["negative_saddle_patch"])
    paint = _blend(paint, _rgb("#51ffd2"), .98 * masks["fusion_necks"])
    paint = _blend(paint, _rgb("#fff4b0"), .97 * masks["neck_rims"])
    paint = _blend(paint, _rgb("#160020"), .98 * masks["transmembrane_pores"])
    paint = _blend(paint, _rgb("#ff3251"), .96 * masks["cleavage_tears"])
    paint = _blend(paint, _rgb("#502070"), .88 * masks["broken_membrane_lips"])
    paint = _blend(paint, _rgb("#a6ff5c"), .93 * masks["healed_collision_seams"])

    hue_null = np.full((S, S), .035, np.float32)
    levels = (.40, .88, .69, .24, .58, .96, .75, .50, .18, .82, .31, .64)
    for (name, mask), level in zip(masks.items(), levels):
        hue_null = hue_null * (1.0 - mask) + float(level) * mask
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    metal = _write_channel(7, masks, (
        ("positive_bilayer_face", 232), ("positive_saddle_patch", 174),
        ("protein_rafts", 252), ("vesicle_buds", 204),
        ("negative_bilayer_face", 48), ("negative_saddle_patch", 82),
        ("fusion_necks", 116), ("neck_rims", 246),
        ("transmembrane_pores", 18), ("cleavage_tears", 138),
        ("broken_membrane_lips", 66), ("healed_collision_seams", 196),
    ))
    rough = _write_channel(238, masks, (
        ("positive_bilayer_face", 72), ("positive_saddle_patch", 118),
        ("protein_rafts", 28), ("vesicle_buds", 146),
        ("negative_bilayer_face", 188), ("negative_saddle_patch", 214),
        ("fusion_necks", 96), ("neck_rims", 44),
        ("transmembrane_pores", 252), ("cleavage_tears", 168),
        ("broken_membrane_lips", 226), ("healed_collision_seams", 132),
    ))
    coat = _write_channel(11, masks, (
        ("negative_bilayer_face", 234), ("negative_saddle_patch", 176),
        ("fusion_necks", 252), ("neck_rims", 216),
        ("transmembrane_pores", 84), ("cleavage_tears", 198),
        ("positive_bilayer_face", 54), ("positive_saddle_patch", 94),
        ("protein_rafts", 126), ("vesicle_buds", 162),
        ("broken_membrane_lips", 32), ("healed_collision_seams", 146),
    ))

    marks = tuple((name, mask, banks[name]) for name, mask in masks.items())
    if any(float(mask.std()) < .0015 for _name, mask, _bank in marks):
        raise ValueError("VM-I1 contains a visually flat semantic family")
    return Grammar(marks, _f(paint), _f(hue_null), (metal, rough, coat))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fpe_violet_membrane": _cubic_bilayer,
}
PETRI_IDS = tuple(BUILDERS)
HUES = {"fpe_violet_membrane": (.86, .51)}


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
    return "fractured-wilds-petri-violet-membrane-vm-i1: 1 isolated candidate"


__all__ = ["BUILDERS", "PETRI_IDS", "HUES", "_authored", "_entry",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "install_into_engine", "owner_unions"]
