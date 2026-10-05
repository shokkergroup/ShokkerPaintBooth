# -*- coding: utf-8 -*-
"""SHOKKER-IZE — turn ANY flat paint/image into an angle-reactive color-shift
finish by auto-generating an optimal spec map from the ART'S OWN GEOMETRY.

MEGA FEATURE 2 (owner mandate 2026-06-13). One click -> the proven "four-dial
winner physics" recovered from the owner's Blood Marble forensics, applied to
whatever paint is on the car:

    M (metal / R channel)      ~252  amplifier rail, +/- the art's micro texture
    B (clearcoat / B channel)  255   railed flat (power supply)
    G (roughness / G channel)  30..78 ultra-gloss floor + aperture lanes that
                                      TRACE the paint's OWN edges + relief

VIRAL PRESETS (2026-06-13). One art, many vibes. Each preset is a DIFFERENT
spec RECIPE over the same lane geometry — it only re-dials the four winner
knobs (metal rail height, metal micro-texture punch, gloss floor, aperture
lane gain) while staying on the proven, physically-valid contract: the metal
rail stays HIGH (amplifier), the clearcoat stays a flat HIGH power supply, and
roughness stays a gloss FLOOR with the design carved as aperture LANES. No
preset can make a muddy or invalid surface — the rails are clamped.

    "subtle"   Subtle Sheen   — gentle satin flash; quiet floor, soft lanes.
    "balanced" Balanced       — the FRACTURED MINDS winner (the default).
    "inferno"  Inferno        — MAX color-shift; deepest floor, widest +
                                hottest lanes, punchiest micro-texture.
    "chrome"   Chrome Flake   — liquid-chrome mirror; metal railed to the top
                                everywhere, tight bright lanes.
    "ghost"    Ghost          — dark phantom that only ignites on the finest
                                edges; deep floor, restrained metal, fine lanes.

This module is ADDITIVE and READ-ONLY toward the rest of the engine: it REUSES
``engine.expansions.fractured_minds_soul_2026._lanes_from_art`` (the exact lane
extractor behind the winner) rather than reinventing it, and the winner
constants (``_FM_M`` / ``_FM_G_FLOOR`` / ``_FM_G_LANE``) are imported from the
same module so the physics can never drift from FRACTURED MINDS.

Public API (BACKWARD-COMPATIBLE):
    shokkerize(paint_rgb, intensity=1.0, preset="balanced", options=None)
                                                    -> HxWx3 uint8 spec (R/G/B = M/G/B)
    shokkerize_to_tga(paint_path, out_path, intensity=1.0, preset="balanced")
    list_presets()                                  -> ordered preset metadata

Importing this module does NOT boot the heavy registry — it only pulls the lane
helper + constants from fractured_minds_soul_2026, which import cleanly on their
own (numpy + cv2 only).
"""
from __future__ import annotations

import os

import numpy as np
import cv2

# Reuse the PROVEN lane extractor and winner contract from FRACTURED MINDS.
# Importing is cleaner than copying: the physics stays single-sourced, so any
# future retune of the winner automatically flows through Shokker-ize too.
from engine.expansions.fractured_minds_soul_2026 import (
    _lanes_from_art as _fm_lanes_from_art,
    _FM_M,
    _FM_G_FLOOR,
    _FM_G_LANE,
)

# Work resolution for lane extraction. Matches FRACTURED MINDS' _WORKF so the
# hairline lanes come out visually identical after the resize back to native.
_WORKF = 768

# Synthesis resolution CAP for the angle-reactive fields (flake/flow/shimmer).
# Big enough that fine flake facets stay crisp (well above the 768 lane work
# res), capped so a native 2048 render synthesizes here and cubic-upsamples —
# keeps the spec pass comfortably ~1s (render-time doctrine: ~1s, never >3s),
# with headroom even when the machine is under heavy concurrent load.
_SYNF = 896


# ---------------------------------------------------------------------------
# ANGLE-REACTIVE MICRO-PHYSICS (2026-06-13 viral retune).
#
# The proven winner contract gave us art-tracing aperture LANES (great for
# carving the design's geometry into the gloss), but the metal channel was a
# near-flat rail (std ~2-4) and a FLAT paint shokker-ized to a FLAT spec — zero
# sparkle, zero per-angle travel, every preset the same look at a different
# strength. Real Shokker finishes come ALIVE because the METAL channel carries
# structured FLAKE (per-facet sparkle that twinkles as the panel turns) and the
# ROUGHNESS channel carries structured SHEEN FLOW (sweeps that travel the
# highlight). These helpers synthesize that structure so EVERY preset is a
# distinct physical surface and works even on a plain solid color, while the
# rails (metal HIGH, clearcoat flat HIGH, roughness a gloss floor) stay clamped
# so nothing can ever go muddy.
#
# All fields are generated at _WORKF and resized with the lanes, so cost is the
# same single 768 pass the winner already paid.
# ---------------------------------------------------------------------------

def _value_noise(h, w, cell, seed):
    """Smooth value noise in 0..1 (bilinear-upsampled lattice). Cheap + tileable
    enough for flake/flow fields; deterministic per ``seed``."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    gh = max(2, int(round(h / max(1.0, cell))) + 1)
    gw = max(2, int(round(w / max(1.0, cell))) + 1)
    lattice = rng.random((gh, gw), dtype=np.float32)
    return cv2.resize(lattice, (w, h), interpolation=cv2.INTER_CUBIC)


# Internal compute cap for the SMOOTH fields (flow/shimmer). They are very
# low-frequency (a handful of cycles across the whole image), so computing them
# on a small grid and cubic-upsampling is visually identical and far cheaper
# than the per-pixel sin/mgrid at native — keeps the spec pass ~1s.
_SMOOTHF = 512


def _flake_field(h, w, density, grain, seed, sharp=0.86):
    """A metallic-FLAKE field in 0..1: bright isolated facets over a dark bed.

    ``density`` (0..1) ~ how many facets ignite; ``grain`` ~ facet size in px
    (smaller = finer pigment). High-frequency value noise gated by a threshold
    so the result is mostly dark with sparse hot pins — the spatial signature
    that twinkles facet-by-facet as the surface rotates through the light.

    2026-06-13 SURVIVAL retune: facets are built at TWO scales and the threshold
    keeps the brightest peaks as crisp pins. The grain floor was raised (>=2.4)
    and a coarse companion layer added so the facets are big enough to SURVIVE
    the work->native->display resamples (the old sub-2px pins washed out to a
    dead-flat rail on plain solids — zero sparkle). Output is dark-bed + sparse
    bright facets, but now the bright facets are spatially real after resize.
    """
    n = _value_noise(h, w, max(2.4, grain), seed)
    # one finer companion layer so facets are a spread of sizes (some large
    # enough to survive resampling, some glitter-fine). Two octaves keeps the
    # cost ~1 noise pass (render-time doctrine) while still breaking up uniform
    # facet size — a third octave was measurably slower for little visual gain.
    n = 0.66 * n + 0.34 * _value_noise(h, w, max(1.6, grain * 0.55), seed + 7919)
    thr = float(np.clip(1.0 - density, 0.0, 0.985))
    f = np.clip((n - thr) / max(1e-3, (1.0 - thr)), 0.0, 1.0)
    # sharpen into crisp facets (gamma) so flakes read as points, not a haze
    f = np.power(f, 1.0 + 6.0 * sharp)
    return f.astype(np.float32)


def _shimmer_field(h, w, seed, scale=150.0):
    """A smooth large-scale undulation in -1..1 (mean ~0). Gives the roughness
    channel slow, organic relief so the calm surface BETWEEN flakes/lanes still
    has somewhere for the highlight to travel — without this a plain solid color
    shokker-izes to a perfectly flat roughness (one dead static hot dot, zero
    'comes alive'). Two octaves so it reads as liquid sheen, not a single blob.
    """
    gh = min(h, _SMOOTHF)
    gw = min(w, _SMOOTHF)
    sc = scale * gw / float(w)  # keep undulation period constant after upscale
    a = _value_noise(gh, gw, sc, seed) - 0.5
    b = _value_noise(gh, gw, max(8.0, sc * 0.42), seed + 4441) - 0.5
    s = (0.68 * a + 0.32 * b) * 2.0  # back to ~-1..1
    s = np.clip(s, -1.0, 1.0).astype(np.float32)
    if (gh, gw) != (h, w):
        s = cv2.resize(s, (w, h), interpolation=cv2.INTER_CUBIC)
    return s


def _flow_field(h, w, angle_deg, freq, seed, jitter=0.35):
    """A directional brushed-metal SHEEN-FLOW field in 0..1: soft anisotropic
    streaks along ``angle_deg``. Wavy (domain-warped) so it reads as liquid
    metal flow, not a ruler grid. Drives the roughness so the mirror highlight
    SWEEPS along the flow as the light moves — the chrome 'liquid' behavior.

    Computed on a capped grid (the streaks are low-frequency) then cubic-resized
    to (h, w): visually identical, but the costly per-pixel sin/mgrid runs on a
    fraction of the pixels.
    """
    gh = min(h, _SMOOTHF)
    gw = min(w, _SMOOTHF)
    ys, xs = np.mgrid[0:gh, 0:gw].astype(np.float32)
    # scale coords back to the full-image span so freq stays in image cycles
    xs *= (w / float(gw)); ys *= (h / float(gh))
    th = np.deg2rad(angle_deg)
    proj = xs * np.cos(th) + ys * np.sin(th)
    warp = (_value_noise(gh, gw, 60.0 * gw / float(w), seed + 333) - 0.5) * (jitter * 80.0)
    s = np.sin((proj + warp) * (2.0 * np.pi * freq / max(h, w)))
    f = (s * 0.5 + 0.5).astype(np.float32)
    if (gh, gw) != (h, w):
        f = cv2.resize(f, (w, h), interpolation=cv2.INTER_CUBIC)
    return f


# ---------------------------------------------------------------------------
# PRESETS — different spec RECIPES over the same proven contract.
#
# Each preset is a dict of dials, all centred on the FRACTURED MINDS winner
# ("balanced" == the winner verbatim). They re-shape the four knobs only:
#
#   m_base     metal rail height (channel R). Winner = _FM_M (252). Stays HIGH
#              (>=210) so the surface is always a strong amplifier, never matte.
#   m_tex      micro-texture punch added to the metal rail (+/- the band relief).
#              Winner = 6.0. Higher = more sparkle/grain riding the rail.
#   g_floor    gloss FLOOR (channel G, the calm mirror between lanes). Winner =
#              _FM_G_FLOOR (30). Lower = glassier calm; higher = more satin.
#   g_lane     aperture lane PEAK (channel G where the design ignites). Winner =
#              _FM_G_LANE (78). The floor->lane spread is the angle-flash drama.
#   lane_gain  how strongly the design's geometry drives toward g_lane. Winner =
#              1.0. >1 widens the lit area; <1 keeps only the strongest edges.
#   g_clamp    (lo, hi) hard clamp on the final roughness channel. Keeps every
#              preset physically valid (no fully-flat or runaway-rough pixels).
#   cc         clearcoat channel (B), the flat power-supply rail. Winner = 255.
#
# 2026-06-13 ANGLE-REACTIVE dials (each preset is now a DISTINCT surface, not a
# strength of one look). These add structured flake + sheen flow so the finish
# twinkles and the highlight travels as the panel turns — and so a FLAT paint
# still gets a real finish (the old presets gave a solid color a dead-flat spec):
#
#   flake_d    flake density 0..1 (fraction of facets that ignite). 0 = none.
#   flake_g    flake grain in work-px (facet size; smaller = finer pigment).
#   flake_m    how hard flakes drive the METAL channel (sparkle amplitude).
#   flake_g_dip how hard a flake facet sharpens the ROUGHNESS down (per-facet
#              mirror pin — this is what makes flakes individually twinkle).
#   flow_ang   brushed-flow angle (deg) for the sheen-sweep field; None = off.
#   flow_freq  flow streak frequency; flow_amp = its roughness amplitude.
#   m_floor_dip low-metal patches so the metal channel has spatial CONTRAST
#              (a uniformly railed metal can't sparkle — it needs darker bed).
#   shimmer    smooth large-scale roughness undulation amplitude (G units). This
#              is the lifeline for PLAIN SOLIDS: with no design lanes, the calm
#              surface would be dead-flat; the shimmer gives the highlight a slow
#              liquid sheen to travel across so even a solid color comes alive.
#
# "intensity" (0..1) still multiplies lane_gain AND the structure amplitudes on
# top of the preset so the old slider keeps working AND composes with the preset.
# ---------------------------------------------------------------------------
_PRESETS = {
    "subtle": {
        "label": "Subtle Sheen",
        "blurb": "Gentle satin flash — fine even pearl, quiet mirror.",
        "m_base": 244.0,
        "m_tex": 4.0,
        "g_floor": 40.0,
        "g_lane": 72.0,
        "lane_gain": 0.80,
        "g_clamp": (24, 104),
        "cc": 252,
        # fine, dense, gentle pearl flake — tasteful even shimmer. Bigger grain
        # + higher amplitude so the pearl survives the resize and reads as a
        # real fine sparkle (not a dead rail) even on a plain solid color.
        "flake_d": 0.32, "flake_g": 3.0, "flake_m": 16.0, "flake_g_dip": 24.0,
        "flow_ang": None, "flow_freq": 0.0, "flow_amp": 0.0,
        "m_floor_dip": 10.0, "shimmer": 7.0,
    },
    "balanced": {
        "label": "Balanced",
        "blurb": "The crowd-pleaser — winner lanes + lively metal flake.",
        "m_base": _FM_M,          # 252
        "m_tex": 6.0,
        "g_floor": _FM_G_FLOOR,   # 30
        "g_lane": _FM_G_LANE,     # 78
        "lane_gain": 1.05,
        "g_clamp": (10, 118),
        "cc": 255,
        # medium scattered flake riding the proven lanes — lively but tasteful.
        # Punchier flake + a slow shimmer so a SOLID also comes alive, while a
        # busy design still keeps its readable lanes (the floor stays low).
        "flake_d": 0.30, "flake_g": 3.4, "flake_m": 30.0, "flake_g_dip": 46.0,
        "flow_ang": None, "flow_freq": 0.0, "flow_amp": 0.0,
        "m_floor_dip": 22.0, "shimmer": 9.0,
    },
    "inferno": {
        "label": "Inferno",
        "blurb": "Aggressive deep metallic flake — hottest, widest color-shift.",
        "m_base": 253.0,
        "m_tex": 14.0,
        "g_floor": 16.0,
        "g_lane": 108.0,
        "lane_gain": 1.45,
        "g_clamp": (6, 138),
        "cc": 255,
        # coarse, deep, punchy flake + a wavy heat-shimmer roughness band — the
        # widest floor->lane spread (deepest flash) and the most violent flake.
        "flake_d": 0.40, "flake_g": 6.5, "flake_m": 42.0, "flake_g_dip": 70.0,
        "flow_ang": 24.0, "flow_freq": 5.0, "flow_amp": 22.0,
        "m_floor_dip": 38.0, "shimmer": 12.0,
    },
    "chrome": {
        "label": "Chrome Flake",
        "blurb": "Liquid-chrome mirror — directional brushed sweeps, railed metal.",
        "m_base": 255.0,
        "m_tex": 6.0,
        "g_floor": 14.0,
        "g_lane": 48.0,
        "lane_gain": 0.85,
        "g_clamp": (5, 84),
        "cc": 255,
        # tight bright micro-flake + DOMINANT directional brushed-metal flow
        # (the flow is the star — it makes the mirror SWEEP like liquid metal).
        # Lower density / finer grain than the others -> a mirror, not glitter.
        "flake_d": 0.20, "flake_g": 2.2, "flake_m": 14.0, "flake_g_dip": 34.0,
        "flow_ang": 18.0, "flow_freq": 9.0, "flow_amp": 34.0,
        "m_floor_dip": 14.0, "shimmer": 4.0,
    },
    "ghost": {
        "label": "Ghost",
        "blurb": "Dark phantom — sparse hard pins that ignite on movement.",
        "m_base": 232.0,
        "m_tex": 5.0,
        "g_floor": 60.0,
        "g_lane": 102.0,
        "lane_gain": 0.74,
        "g_clamp": (30, 134),
        "cc": 248,
        # very sparse but VERY HOT pin-flake: the few facets that fire punch the
        # metal hard above the bed (rail 232 + 56 -> 255 mirror pins) and dip the
        # roughness deep, so a dark phantom surface erupts into sharp glints only
        # as it turns. The deepest satin bed of all the presets.
        "flake_d": 0.13, "flake_g": 3.2, "flake_m": 56.0, "flake_g_dip": 60.0,
        "flow_ang": None, "flow_freq": 0.0, "flow_amp": 0.0,
        "m_floor_dip": 30.0, "shimmer": 11.0,
    },
}

# Structure-dial keys (used by _resolve_preset override + safe defaults).
_STRUCT_KEYS = ("flake_d", "flake_g", "flake_m", "flake_g_dip",
                "flow_ang", "flow_freq", "flow_amp", "m_floor_dip", "shimmer")

# Ordered for the UI (the order the one-click buttons appear, left->right).
_PRESET_ORDER = ["subtle", "balanced", "inferno", "chrome", "ghost"]

DEFAULT_PRESET = "balanced"


def list_presets():
    """Return ordered preset metadata for the UI:
    ``[{"id":..,"label":..,"blurb":..}, ...]`` in display order."""
    out = []
    for pid in _PRESET_ORDER:
        p = _PRESETS[pid]
        out.append({"id": pid, "label": p["label"], "blurb": p["blurb"]})
    return out


def _resolve_preset(preset, options):
    """Merge a named preset with any per-call ``options`` overrides.

    ``preset`` may be a preset id (str) or already a dict of dials. ``options``
    (dict | None) overrides individual dials on top — used by power callers /
    the API to nudge a preset without inventing a new one. Unknown names fall
    back to the proven default so the feature never hard-fails on bad input.
    """
    if isinstance(preset, dict):
        base = dict(_PRESETS[DEFAULT_PRESET])
        base.update(preset)
    else:
        key = str(preset or DEFAULT_PRESET).strip().lower()
        base = dict(_PRESETS.get(key, _PRESETS[DEFAULT_PRESET]))
    # Backfill any structure dials a (possibly older/custom) dict preset omitted,
    # so the synthesis below never KeyErrors and a bare dict still gets a finish.
    for k in _STRUCT_KEYS:
        base.setdefault(k, _PRESETS[DEFAULT_PRESET].get(k))
    if isinstance(options, dict):
        scalar_keys = ("m_base", "m_tex", "g_floor", "g_lane", "lane_gain", "cc") + _STRUCT_KEYS
        for k in scalar_keys:
            if k in options and options[k] is not None:
                # flow_ang may legitimately be None (flow off) — only floatable here
                try:
                    base[k] = float(options[k])
                except (TypeError, ValueError):
                    pass
        if "g_clamp" in options and options["g_clamp"]:
            try:
                lo, hi = options["g_clamp"]
                base["g_clamp"] = (float(lo), float(hi))
            except Exception:  # noqa: BLE001
                pass
    return base


def _as_float_rgb(paint_rgb) -> np.ndarray:
    """Coerce any HxW(x{1,3,4}) array (uint8 or float) to HxWx3 float32 in 0..1."""
    a = np.asarray(paint_rgb)
    if a.ndim == 2:
        a = np.repeat(a[:, :, None], 3, axis=2)
    a = a[:, :, :3].astype(np.float32)
    # uint8-style range -> normalize. Floats already in 0..1 pass through.
    if a.size and float(a.max()) > 1.5:
        a = a / 255.0
    return np.clip(a, 0.0, 1.0)


def shokkerize(paint_rgb, intensity: float = 1.0, preset="balanced",
               options=None) -> np.ndarray:
    """Generate a winner color-shift spec from a paint image's OWN geometry.

    BACKWARD-COMPATIBLE: ``shokkerize(paint)`` and ``shokkerize(paint, 0.7)``
    behave exactly as before (the default preset is the FRACTURED MINDS
    winner). ``preset`` / ``options`` are additive keyword args.

    Args:
        paint_rgb: HxW(x{1,3,4}) image, uint8 (0..255) or float (0..1). The
            FLAT paint/art the owner wants to make angle-reactive.
        intensity: 0..1 — how aggressive the shift is. Multiplies the preset's
            aperture lane gain (1.0 = the preset as designed; lower = subtler
            flash). The metal rail and the flat clearcoat are rails and do NOT
            scale, so even intensity 0 stays a valid glossy color-shift surface.
        preset: a preset id ("subtle"/"balanced"/"inferno"/"chrome"/"ghost") or
            a dict of dials. Unknown ids fall back to the proven default.
        options: optional dict overriding individual dials on top of the preset
            (m_base / m_tex / g_floor / g_lane / lane_gain / cc / g_clamp).

    Returns:
        HxWx3 uint8 spec, SAME H/W as the input, with channels:
            [..., 0] = M  (metal,     high amplifier rail +/- micro texture)
            [..., 1] = G  (roughness, gloss floor .. aperture lanes, clamped)
            [..., 2] = B  (clearcoat, flat high power supply)
    """
    art = _as_float_rgb(paint_rgb)
    fh, fw = art.shape[:2]

    intensity = float(np.clip(intensity, 0.0, 1.0))
    p = _resolve_preset(preset, options)

    # Extract lanes at the proven work resolution, then resize back to native.
    # _fm_lanes_from_art is hairline-fine by construction (1-2px gradients), so
    # working at 768 and upscaling keeps the lanes crisp while bounding cost.
    work = cv2.resize(art, (_WORKF, _WORKF), interpolation=cv2.INTER_AREA) \
        if (fh, fw) != (_WORKF, _WORKF) else art
    lane, mtex = _fm_lanes_from_art(work)

    # Preset lane gain * the user intensity (both compose).
    lane = np.clip(lane * float(p["lane_gain"]) * intensity, 0.0, 1.0)

    # Deterministic per-paint seed so the flake/flow pattern is stable for a
    # given art + preset (re-clicking the same look gives the same surface) but
    # differs between different paints (each car gets its own flake scatter).
    # zlib.crc32 (not Python's salted hash) keeps the scatter identical across
    # process restarts, so a finish never silently changes between sessions.
    import zlib
    luma = (0.299 * work[..., 0] + 0.587 * work[..., 1] + 0.114 * work[..., 2])
    pkey = zlib.crc32(str(preset).encode("utf-8", "ignore"))
    seed = (int(abs(float(luma.mean()) * 1000.0)) ^ pkey ^ 0x5BD1E995) & 0x7FFFFFFF

    # ---- ANGLE-REACTIVE STRUCTURE -------------------------------------------
    # Synthesized at a CAPPED resolution (cost guard) then resized to native.
    # The old code generated this at 768 and resized the COMBINED channel down
    # with a blurring LINEAR filter (768 -> 1024/2048 = a DOWNscale relative to
    # the flake's native pixel grid for sub-1k arts), which washed the sparse
    # flake pins out to a dead rail on plain solids (no twinkle). We now synth a
    # touch finer than the old 768 (so facets are spatially real) and upsample
    # the composed channels to native with CUBIC (crisp, no extra blur). _SYNF
    # caps native renders so the value-noise pass stays ~1s (render-time doctrine).
    synf = int(min(max(fh, fw, _WORKF), _SYNF))
    rscale = synf / float(_WORKF)  # keep facet/cell physical size constant

    # FLAKE: bright sparse metallic facets. Each facet (a) pushes the METAL rail
    # UP (sparkle) and (b) sharply dips the ROUGHNESS down to a near-mirror pin,
    # so the facet catches a hard glint that twinkles as the panel turns. Built
    # from the design seed so it exists even on a flat solid color.
    flake = _flake_field(synf, synf, float(p["flake_d"]), float(p["flake_g"]) * rscale,
                         seed) if float(p["flake_d"]) > 0 else None

    # M floor-dip: a slow low-metal bed so the railed metal has spatial CONTRAST
    # (a uniformly maxed metal channel can't sparkle — it needs darker between
    # the flakes). Smooth + subtle; never drops below the >=210 amplifier rail.
    m_dip = _value_noise(synf, synf, 96.0 * rscale, seed + 11) if float(p["m_floor_dip"]) > 0 else None

    # FLOW: directional brushed-metal sheen streaks. Modulates ROUGHNESS so the
    # mirror highlight SWEEPS along the flow as the light moves — chrome/inferno.
    flow = None
    if p["flow_ang"] is not None and float(p["flow_amp"]) > 0:
        flow = _flow_field(synf, synf, float(p["flow_ang"]), float(p["flow_freq"]),
                           seed + 21)

    # SHIMMER: slow large-scale roughness undulation. This is what lets a PLAIN
    # SOLID come alive — with no design lanes the calm surface would be flat, so
    # the shimmer gives the highlight a liquid sheen to travel across. It also
    # adds organic body to busy designs without touching the readable lanes
    # (it is low-frequency, so it never competes with the hairline lane carving).
    shimmer = None
    if float(p.get("shimmer", 0.0)) > 0:
        shimmer = _shimmer_field(synf, synf, seed + 57, scale=150.0 * rscale)

    # Compose METAL: rail + design micro-texture + flake sparkle - floor dip.
    # mtex/lane come from the FM extractor at _WORKF; resize them to the synth
    # grid so all the fields combine at one resolution.
    if (synf, synf) != mtex.shape[:2]:
        mtex = cv2.resize(mtex, (synf, synf), interpolation=cv2.INTER_LINEAR)
        lane = cv2.resize(lane, (synf, synf), interpolation=cv2.INTER_LINEAR)
    M = float(p["m_base"]) + float(p["m_tex"]) * mtex
    if flake is not None:
        M = M + float(p["flake_m"]) * flake * (0.4 + 0.6 * intensity)
    if m_dip is not None:
        M = M - float(p["m_floor_dip"]) * (1.0 - m_dip) * (0.4 + 0.6 * intensity)

    # Compose ROUGHNESS: gloss floor -> aperture lanes (the proven shift),
    # then a slow shimmer gives the calm surface somewhere for the highlight to
    # travel (so even a solid lives), then flow sweeps add/remove sheen, then
    # flakes punch hard mirror pins.
    G = float(p["g_floor"]) + (float(p["g_lane"]) - float(p["g_floor"])) * lane
    if shimmer is not None:
        G = G + float(p["shimmer"]) * shimmer * (0.5 + 0.5 * intensity)
    if flow is not None:
        G = G + float(p["flow_amp"]) * (flow - 0.5) * 2.0 * (0.4 + 0.6 * intensity)
    if flake is not None:
        # facets are LOCAL MIRRORS: subtract toward gloss where a flake fires
        G = G - float(p["flake_g_dip"]) * flake * (0.4 + 0.6 * intensity)

    # Resize the composed channels to native. FLAKE pins demand a sharp filter
    # so they don't blur back into the rail: when UPsampling we use cubic (crisp
    # but smooth); when the synth grid already matches native this is a no-op.
    if (fh, fw) != (synf, synf):
        interp = cv2.INTER_CUBIC if (fh * fw) >= (synf * synf) else cv2.INTER_AREA
        M = cv2.resize(M, (fw, fh), interpolation=interp)
        G = cv2.resize(G, (fw, fh), interpolation=interp)

    g_lo, g_hi = p["g_clamp"]
    out = np.zeros((fh, fw, 3), np.uint8)
    # Metal rail clamped HIGH (>=210) so the surface is always a strong
    # amplifier — no preset can flatten it into a matte color.
    out[:, :, 0] = np.clip(M, 210, 255).astype(np.uint8)        # metal rail + flake
    out[:, :, 1] = np.clip(G, g_lo, g_hi).astype(np.uint8)      # gloss floor + lanes + flow + flake pins
    out[:, :, 2] = np.clip(float(p["cc"]), 200, 255)            # clearcoat railed flat high
    return out


def shokkerize_to_tga(paint_path: str, out_path: str, intensity: float = 1.0,
                      preset="balanced", options=None) -> str:
    """Read a paint image, shokker-ize it, and write a car_spec-style TGA.

    The spec is written as a 3-channel RGB image (R=M, G=G, B=clearcoat)
    matching the engine's spec-map convention. Uses PIL for both read and write
    so the on-disk R/G/B channels are correct and TGA output works across
    OpenCV builds (some lack a TGA writer). The format follows the output file
    extension (``.tga`` -> Targa, ``.png`` -> PNG, etc.).

    Returns the output path.
    """
    from PIL import Image as PILImage

    try:
        img = PILImage.open(paint_path).convert("RGB")
    except FileNotFoundError:
        raise
    except Exception as e:  # noqa: BLE001
        raise IOError(f"could not read paint image {paint_path}: {e}")

    rgb = np.asarray(img, dtype=np.uint8)
    spec_rgb = shokkerize(rgb, intensity=intensity, preset=preset, options=options)

    out_img = PILImage.fromarray(spec_rgb, "RGB")
    ext = os.path.splitext(out_path)[1].lower()
    fmt = "TGA" if ext in (".tga", ".targa") else None  # else let PIL infer
    if fmt:
        out_img.save(out_path, fmt)
    else:
        out_img.save(out_path)
    return out_path
