# -*- coding: utf-8 -*-
"""FRACTURED CATLIB (2026-07-30) — shared machinery for the 10-category
FRACTURED expansion (owner brief 2026-07-30: color diversity mandate, 200 new
finishes). This is the GENERALIZED version of the shipped
engine/expansions/fractured_morpho_2026.py pipeline (which stays untouched,
gates green: 50/50, mean 757ms @2048):

  structural generator -> optical-thickness field T (0..1) at <=640^2
  -> one fancy-index into a precomputed 1024-entry thin-film interference LUT
  -> HERO-HUE WINDOW remap (hues/hspan per recipe, anchor picked per macro
     domain, luma texture re-applied so satboost can't flatten fineness)
  -> MACRO COMPOSITION layer (7 kinds + category-specific extras via
     extra_macro) drives phase offset (tmod) AND value drama (vd)
  -> ambient bloom / anti-dead-black floor / sparkle / gray / flash dials
  -> ONE cubic upscale to work res (_WORK=1152); lru_cached art shared by
     paint_fn + spec_fn (spec mirrors paint — the uniqueness rule)
  -> spec_fn carves M/R lanes + MACRO-DOMAIN CLEARCOAT (big coherent Cc cells
     from the blocky domain map + hue-domain accent) — the ghost-shift
     doctrine. Nothing iterates at render res.

A category module supplies ONLY: structural generators (engine name -> fn
(res, seed, **eargs) -> T field 0..1), recipe dicts grouped in GROUPS, and a
CategoryKit instance. See engine/expansions/fractured_molten_2026.py for the
reference pilot and _fracx_work/WAVE_PLAYBOOK.md for the full recipe.

RECIPE SCHEMA (same as MORPHO):
  name / engine / eargs / seed / lut=(t_lo,t_hi nm, gamma, sat, phase) /
  val=paint crush value / hues=[anchors in turns] / hspan=window half-width /
  satboost / macro=(kind, params) / vd=(shadow, flash) / tmod=phase follow /
  kw=(ambient, ambient_sigma, floor, sparkle, gray, flash,
      mswing, mfloor, rswing, rceil, ccboost, ccpat) / desc
Every recipe must carry a dated audit comment (owner mandate).

PERF DOCTRINE (binding): generators compute at <=_GEN^2, one cubic upscale
to _WORK, nothing iterates at render res, fully vectorized numpy/cv2.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

_WORK = 1152
_GEN = 640          # structural generators run here, then cubic-up to _WORK
_MAC = 192          # macro composition layer resolution (then cubic-up)
# M7 audit revision (MORPHO 2026-07-30): uniform paint-value recalibration.
# The old 0.10-0.22 crush rendered the paint channel near-black while the
# spec channel screamed -> M5 incoherence. Gain lifts the SAME art (no
# recolor, no structure change) so microstructure reads in the paint channel.
_VAL_GAIN = 2.4
_LUT_N = 1024

# ════════════════════════════════════════════════════════════════════════════
# SMALL VECTOR HELPERS (public: category generators are built from these)
# ════════════════════════════════════════════════════════════════════════════

def rng(seed, salt=0):
    return np.random.default_rng([(int(seed) * 100003) & 0x7FFFFFFF, int(salt) & 0x7FFFFFFF])


def n01(a):
    a = np.asarray(a, np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def gauss(a, s):
    return cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), float(s))


def sstep(a, b, x):
    t = np.clip((np.asarray(x, np.float32) - a) / (b - a + 1e-9), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def frac(a):
    a = np.asarray(a, np.float32)
    return (a - np.floor(a)).astype(np.float32)


def coords(res):
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    return yy, xx


def h2(cx, cy, salt=0):
    """Deterministic 2D cell hash -> 0..1 (per-scale / per-domain jitter)."""
    return frac(np.sin(cx * 127.1 + cy * 311.7 + salt * 74.7) * 43758.5453)


def fbm(h, w, r, octaves=4, base=4, gain=0.55):
    """Multi-octave value noise (cubic-upscaled random grids). Vectorized."""
    acc = np.zeros((h, w), np.float32)
    amp, tot, res = 1.0, 0.0, int(base)
    for _ in range(int(octaves)):
        g = r.random((res, res)).astype(np.float32)
        acc += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= gain
        res = min(res * 2, max(h, w) + 1)
        if res > max(h, w):
            break
    return acc / max(tot, 1e-9)


def warp_pair(res, seed, salt, amt):
    """Two smooth warp-offset fields (domain warp), amplitude amt in px."""
    sr = res / 640.0
    wu = (fbm(res, res, rng(seed, salt), 3, 5) - 0.5) * float(amt) * sr
    wv = (fbm(res, res, rng(seed, salt + 1), 3, 5) - 0.5) * float(amt) * sr
    return wu.astype(np.float32), wv.astype(np.float32)


def rot(uv, a):
    c, s = np.cos(a), np.sin(a)
    return uv[1] * c + uv[0] * s, -uv[1] * s + uv[0] * c


def worley(res, seed, cells, salt):
    """Jittered-grid Worley: (min distance 0..1, winning cell id hash). 9 taps."""
    g = res / float(cells)
    yy, xx = coords(res)
    cu = np.floor(xx / g); cv = np.floor(yy / g)
    best = np.full((res, res), 1e9, np.float32)
    bid = np.zeros((res, res), np.float32)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            jx = h2(cu + di, cv + dj, salt)
            jy = h2(cu + di, cv + dj, salt + 50)
            fx = (cu + di + 0.15 + 0.7 * jx) * g
            fy = (cv + dj + 0.15 + 0.7 * jy) * g
            d = np.sqrt((xx - fx) ** 2 + (yy - fy) ** 2) / (g * 1.6)
            m = d < best
            best = np.where(m, d, best)
            bid = np.where(m, h2(cu + di, cv + dj, salt + 90), bid)
    return np.clip(best, 0.0, 1.0), bid


# ════════════════════════════════════════════════════════════════════════════
# THIN-FILM INTERFERENCE LUT — the physics core
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=64)
def thinfilm_lut(t_lo, t_hi, gamma, sat, phase):
    """1024-entry RGB LUT: optical thickness (nm) -> reflectance per channel via
    sin^2 phase terms at ~640/550/470nm (two-beam thin-film interference).
    sat<1 pulls toward the pearly mean, sat>1 pushes spectral purity."""
    i = np.arange(_LUT_N, dtype=np.float32) / (_LUT_N - 1)
    T = float(t_lo) + i * (float(t_hi) - float(t_lo))
    lam = np.array([640.0, 550.0, 470.0], np.float32)
    I = np.sin(2.0 * np.pi * T[:, None] / lam[None, :] + float(phase)) ** 2
    rgb = np.clip(I, 0.0, 1.0) ** float(gamma)
    m = rgb.mean(axis=1, keepdims=True)
    rgb = np.clip(m + (rgb - m) * float(sat), 0.0, 1.0)
    return rgb.astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# CATEGORY KIT — one instance per category module. Holds the recipe table,
# the engine registry, the macro composition layer and the cached art, and
# manufactures the (spec_fn, paint_fn) registry pairs.
# ════════════════════════════════════════════════════════════════════════════

class CategoryKit:
    """Generalized MORPHO machinery for one FRACTURED category.

    engines:      {engine_name: fn(res, seed, **eargs) -> T field (0..1, res^2)}
    groups:       {group_name: {finish_id: recipe_dict}}
    tag:          install print tag, e.g. "fractured-molten"
    extra_macro:  optional {kind: fn(r, mp, seed, K) -> (M, D) at r x r} —
                  category-specific macro composition kinds. K is this kit
                  (use K.fbm, K.rng, K.h2, K.sstep, K.n01, K.gauss,
                  K.coords, K.rot, K.warp_pair, K.worley).
    """

    def __init__(self, engines, groups, tag, extra_macro=None,
                 val_gain=_VAL_GAIN, work=_WORK, gen=_GEN, mac=_MAC):
        self.engines = dict(engines)
        self.GROUPS = groups
        self.tag = str(tag)
        self.extra_macro = dict(extra_macro or {})
        self.VAL_GAIN = float(val_gain)
        self.WORK = int(work)
        self.GEN = int(gen)
        self.MAC = int(mac)
        self.ALL = {}
        for _grp in groups.values():
            self.ALL.update(_grp)
        # lru-cached views (shared by paint_fn + spec_fn: spec mirrors paint)
        self.macro_cached = lru_cache(maxsize=16)(self._macro_maps_fid)
        self.art_work_cached = lru_cache(maxsize=8)(self.art_work)

    # -- helper passthroughs for extra_macro authors ----------------------
    rng = staticmethod(rng)
    n01 = staticmethod(n01)
    gauss = staticmethod(gauss)
    sstep = staticmethod(sstep)
    frac = staticmethod(frac)
    coords = staticmethod(coords)
    h2 = staticmethod(h2)
    fbm = staticmethod(fbm)
    warp_pair = staticmethod(warp_pair)
    rot = staticmethod(rot)
    worley = staticmethod(worley)

    # ════════════════════════════════════════════════════════════════════
    # MACRO COMPOSITION LAYER — 7 shared kinds + category extras.
    # Mval: smooth 0..1 value/composition map (value drama + phase offset).
    # Ddom: 0..1 blocky domain map (hue-anchor pick + clearcoat carve cells).
    # ════════════════════════════════════════════════════════════════════

    def macro_maps(self, d):
        seed = int(d["seed"])
        kind, mp = d.get("macro", ("none", {}))
        r = self.MAC
        yy, xx = coords(r)
        u, v = xx / r, yy / r

        def _polar(cx, cy):
            dx = (u - cx) * float(mp.get("squish", 1.0))
            dy = v - cy
            return np.hypot(dx, dy), np.arctan2(dy, dx)

        if kind in self.extra_macro:
            # category-specific kind: author returns (M, D) at r x r
            M, D = self.extra_macro[kind](r, mp, seed, self)
        elif kind == "rings":
            # concentric eye-spot rings around 1-2 centers; ring index = domain
            cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.5))
            dist, _ = _polar(cx, cy)
            if mp.get("two"):
                d2, _ = _polar(float(mp.get("cx2", 0.72)), float(mp.get("cy2", 0.30)))
                dist = np.minimum(dist, d2 * 1.15)
            freq = float(mp.get("freq", 9.0))
            band = 0.5 + 0.5 * np.cos(2.0 * np.pi * freq * dist)
            M = sstep(0.25, 0.75, band)
            M = M * np.clip(1.3 - dist, 0.0, 1.0)                    # fade outward
            D = n01(h2(np.floor(dist * freq), dist * 0.0, 7)
                     + frac(dist * freq) * 0.4
                     + fbm(r, r, rng(seed, 502), 2, 3) * 0.10)
        elif kind == "bands":
            # broad diagonal flash bands over near-black; band index = domain
            ang = float(mp.get("angle", 0.6))
            ru, rv = rot((yy, xx), ang)
            p = ru / r + fbm(r, r, rng(seed, 503), 3, 3) * float(mp.get("warp", 0.22))
            freq = float(mp.get("freq", 3.0))
            w = 0.5 + 0.5 * np.cos(2.0 * np.pi * freq * p)
            M = sstep(float(mp.get("lo", 0.42)), float(mp.get("hi", 0.72)), w)
            M = M * (0.75 + 0.25 * fbm(r, r, rng(seed, 504), 2, 4))
            D = n01(h2(np.floor(p * freq), 0, 11) + frac(p * freq) * 0.25)
        elif kind == "margin":
            # concentric wing-margin banding: luminous band inside a dark rim
            cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.52))
            dist, _ = _polar(cx, cy)
            dist = dist / max(float(mp.get("radius", 0.72)), 1e-3)
            ring = 0.5 + 0.5 * np.cos(2.0 * np.pi * float(mp.get("freq", 3.0)) * (1.0 - dist))
            M = sstep(0.30, 0.80, ring) * sstep(1.15, 0.55, dist)  # dark outside rim
            D = n01(h2(np.floor((1.0 - dist) * float(mp.get("freq", 3.0))), 0, 13)
                     + fbm(r, r, rng(seed, 505), 2, 3) * 0.15)
        elif kind == "rachis":
            # central shaft + directional falloff (feather vane); lanes = domain
            ang = float(mp.get("angle", 0.0))
            ru, rv = rot((yy - r * 0.5, xx - r * 0.5), ang)
            shaft = np.exp(-((rv / r) ** 2) * float(mp.get("shaft", 900.0)))
            flow = 0.5 + 0.5 * np.sin(ru / r * float(mp.get("sweep", 4.0)) + fbm(r, r, rng(seed, 506), 2, 3) * 3.0)
            M = np.clip(shaft * 1.2 + flow * 0.55 * (1.0 - shaft * 0.4), 0.0, 1.0)
            D = n01(h2(np.floor((rv / r + 0.5) * float(mp.get("lanes", 6.0))), 0, 17)
                     + frac((rv / r + 0.5) * float(mp.get("lanes", 6.0))) * 0.2)
        elif kind == "vortex":
            # 1-2 big curl vortices; angular sectors = domain
            cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.5))
            dist, angv = _polar(cx, cy)
            spiral = 0.5 + 0.5 * np.cos(angv * float(mp.get("arms", 2.0))
                                        + dist * float(mp.get("twist", 10.0)))
            M = sstep(0.30, 0.75, spiral) * np.clip(1.25 - dist * 1.1, 0.15, 1.0)
            if mp.get("two"):
                d2, a2 = _polar(float(mp.get("cx2", 0.75)), float(mp.get("cy2", 0.72)))
                s2 = 0.5 + 0.5 * np.cos(a2 * float(mp.get("arms", 2.0)) + d2 * float(mp.get("twist", 10.0)))
                M = np.maximum(M, sstep(0.35, 0.75, s2) * np.clip(1.1 - d2 * 1.4, 0.0, 1.0))
            D = n01(h2(np.floor((angv / np.pi + 1.0) * float(mp.get("sectors", 5.0))), 0, 19)
                     + dist * 0.3)
        elif kind == "continents":
            # big tarnish landmasses; per-continent random = domain
            f = fbm(r, r, rng(seed, 507), int(mp.get("oct", 4)), int(mp.get("base", 3)))
            f = f + warp_pair(r, seed, 508, 6.0)[0] * 0.02
            M = sstep(float(mp.get("lo", 0.38)), float(mp.get("hi", 0.62)), f)
            q = np.clip((f * float(mp.get("cells", 4.0))).astype(np.int32), 0, 63)
            D = n01(h2(q, 0, 23) + M * 0.25)
        elif kind == "domains":
            # coarse worley cells; per-cell random = domain, cell value = Mval
            cells = int(mp.get("cells", 10))
            _, cid = worley(r, seed, cells, int(mp.get("salt", 29)))
            cv = h2(cid, 0, 31)
            M = n01(gauss(cv, 1.2))                                 # smooth-ish patches
            D = n01(h2(cid, 0, 87))   # different salt: brightness NOT locked to anchor
        else:  # "none" — gentle low-freq variation only
            f = fbm(r, r, rng(seed, 509), 2, 3)
            M = 0.45 + 0.35 * (f - 0.5)
            D = n01(np.clip((f * 5.0).astype(np.int32), 0, 63).astype(np.float32) / 8.0)

        Mval = cv2.resize(np.clip(M, 0.0, 1.0).astype(np.float32), (self.GEN, self.GEN),
                          interpolation=cv2.INTER_CUBIC)
        Ddom = cv2.resize(np.clip(D, 0.0, 1.0).astype(np.float32), (self.GEN, self.GEN),
                          interpolation=cv2.INTER_NEAREST)  # keep domains blocky
        return Mval.astype(np.float32), Ddom.astype(np.float32)

    def _macro_maps_fid(self, fid):
        return self.macro_maps(self.ALL[fid])

    # ════════════════════════════════════════════════════════════════════
    # ART ASSEMBLY — thickness field -> interference LUT -> iridescent RGB.
    # Cached per finish id; paint_fn and spec_fn share it (spec mirrors paint).
    # ════════════════════════════════════════════════════════════════════

    def art_work(self, fid):
        """Work-res iridescent art (0..1 HxWx3 float32)."""
        d = self.ALL[fid]
        seed = int(d["seed"])
        GEN = self.GEN
        Mval, Ddom = self.macro_cached(fid)
        T = self.engines[d["engine"]](GEN, seed, **d.get("eargs", {}))
        # phase follows the macro form: color bands align with the composition
        T = frac(np.asarray(T, np.float32) + Mval * float(d.get("tmod", 0.30)))
        lut = thinfilm_lut(*d["lut"])
        idx = np.clip((T * (_LUT_N - 1)).astype(np.int32), 0, _LUT_N - 1)
        rgb = lut[idx]                                                # GEN^2 RGB
        # HERO HUE WINDOW: remap the interference hue into the recipe's
        # restricted gamut (anchor per macro domain when several). Thin-film
        # phase still drives hue travel INSIDE the window; saturation pushed.
        hues = d.get("hues")
        if hues:
            anchors = np.asarray(hues, np.float32)
            hspan = float(d.get("hspan", 0.07))
            # keep the thin-film's own luma texture: the HSV roundtrip +
            # satboost would otherwise compress fine-scale luma detail
            # (fineness gate).
            Lpre = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])
            hsv = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8),
                               cv2.COLOR_RGB2HSV).astype(np.float32)
            h = hsv[:, :, 0] * (1.0 / 179.0)
            if len(anchors) > 1:
                ai = np.clip((Ddom * len(anchors)).astype(np.int32), 0, len(anchors) - 1)
                c = anchors[ai]
            else:
                c = np.full_like(h, anchors[0])
            dh = ((h - c + 0.5) % 1.0) - 0.5
            hn = (c + dh * (hspan * 2.0)) % 1.0
            s = np.clip(hsv[:, :, 1] * (1.0 / 255.0) * float(d.get("satboost", 1.35)) + 0.08, 0, 1)
            hsv_out = np.stack([hn * 179.0, s * 255.0, hsv[:, :, 2]], axis=2)
            rgb = cv2.cvtColor(hsv_out.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32) * (1.0 / 255.0)
            Lpost = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])
            rgb = rgb * (Lpre / np.maximum(Lpost, 1e-3))[..., None]
        # VALUE DRAMA: deep blacks against luminous flash zones (macro-driven).
        shadow, flashv = d.get("vd", (0.30, 1.10))
        rgb = rgb * (float(shadow) + (float(flashv) - float(shadow)) * Mval)[..., None]
        kw = d.get("kw", {})
        # ambient bloom floor (fractured_math.colorize doctrine): a soft wide
        # bloom keeps even the darkest interference nulls off dead-black ->
        # full coverage. All finishing runs at GEN (speed law); ONE cubic
        # upscale to WORK at the end.
        sc = GEN / float(self.WORK)
        # M7 audit revision (MORPHO 2026-07-30): bloom mix halved — the old
        # full-strength mix flattened micro-contrast (paint fine energy ~3x
        # below catalog median). The anti-dead-black floor below is untouched,
        # so coverage holds.
        amb = float(kw.get("ambient", 0.30)) * 0.5
        bloom = cv2.GaussianBlur(rgb, (0, 0), float(kw.get("ambient_sigma", 48)) * sc)
        rgb = rgb * (1.0 - amb) + bloom * amb
        floor = float(kw.get("floor", 0.10))
        L = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])
        lift = np.clip(floor - L, 0.0, 1.0)[..., None]
        rgb = rgb + lift * bloom.mean(axis=(0, 1), keepdims=True) * 2.0
        # crushed micro sparkle — the highest of >=3 frequency bands
        spark = fbm(GEN, GEN, rng(seed, 777), 2, 320)
        rgb = rgb + (spark - 0.5)[..., None] * float(kw.get("sparkle", 0.07))
        # gray dial: per-recipe chroma pull toward the pixel's OWN luma
        # (scattering in aged/thick stacks). Luma micro-structure preserved,
        # so fine energy and the fineness gate are unaffected.
        Lg = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])[..., None]
        gray = float(kw.get("gray", 0.0))
        if gray > 0.0:
            rgb = rgb * (1.0 - gray) + Lg * gray
        # flash dial: chroma gated by luma PEAKS — interference only fires at
        # resonance maxima; the dark body between flashes is dead gray potch.
        fl_r = kw.get("flash")
        if fl_r:
            fl = sstep(float(fl_r[0]), float(fl_r[1]), Lg)
            rgb = Lg + (rgb - Lg) * fl
        rgb = cv2.resize(np.clip(rgb, 0.0, 1.0), (self.WORK, self.WORK), interpolation=cv2.INTER_CUBIC)
        return np.clip(rgb, 0.0, 1.0).astype(np.float32)

    # ════════════════════════════════════════════════════════════════════
    # REGISTRY PAIR FACTORY — the ghost-shift spec contract.
    # ════════════════════════════════════════════════════════════════════

    def mk(self, fid):
        """-> (spec_fn, paint_fn) per the registry contract:
        spec_fn(shape, mask, seed, sm) -> HxWx4 uint8 (M,R,Cc,A)
        paint_fn(paint, shape, mask, seed, pm, bb) -> HxWx3 float"""
        val = float(self.ALL[fid].get("val", 0.16))
        WORK = self.WORK
        VAL_GAIN = self.VAL_GAIN

        def paint_fn(paint, shape, mask, seed, pm, bb):
            fh, fw = int(shape[0]), int(shape[1])
            src = np.asarray(paint, np.float32)[:, :, :3]
            if src.size and src.max() > 1.5:
                src = src / 255.0
            m2 = np.asarray(mask, np.float32)
            if m2.ndim == 3:
                m2 = m2[:, :, 0]
            if m2.shape[:2] != (fh, fw):
                m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
            art = cv2.resize(self.art_work_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
            # PAINT VALUE = the color mixer (SOULS doctrine): crush the
            # iridescent art to the recipe value, saturation kept.
            crushed = art * (min(val * VAL_GAIN, 0.85) / max(float(art.max()), 1e-6))
            kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
            out = src * (1.0 - kk) + crushed * kk
            return np.clip(out, 0.0, 1.0).astype(np.float32)

        def spec_fn(shape, mask, seed, sm):
            fh, fw = int(shape[0]), int(shape[1])
            m2 = np.asarray(mask, np.float32)
            if m2.ndim == 3:
                m2 = m2[:, :, 0]
            if m2.shape[:2] != (WORK, WORK):
                m2 = cv2.resize(m2, (WORK, WORK), interpolation=cv2.INTER_LINEAR)
            # carve at WORK from the cached art (no render-res iteration),
            # one uint8 resize at the end — the speed law.
            art = self.art_work_cached(fid)
            L = (0.299 * art[:, :, 0] + 0.587 * art[:, :, 1] + 0.114 * art[:, :, 2]).astype(np.float32)
            # percentile stretch (not min-max): interference luma histograms
            # are tight mid-band — p2/p98 stretch gives the carve real travel.
            _lo, _hi = np.percentile(L, 2.0), np.percentile(L, 98.0)
            pattern = np.clip((L - _lo) / max(float(_hi - _lo), 1e-6), 0.0, 1.0)
            fl = gauss(pattern, 1.2)
            gx = cv2.Sobel(fl, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(fl, cv2.CV_32F, 0, 1, ksize=3)
            edge = n01(np.hypot(gx, gy))
            micro = n01(pattern - gauss(pattern, 2.5))
            # hue-domain map: clearcoat travel follows the interference HUE
            # domains (saturation-weighted) so Cc decorrelates from the
            # luma-derived M/R channels (channel independence gate).
            hsv = cv2.cvtColor((art * 255.0).astype(np.uint8), cv2.COLOR_RGB2HSV)
            hue = hsv[:, :, 0].astype(np.float32) * (1.0 / 179.0)
            satn = n01(hsv[:, :, 1].astype(np.float32))
            hdom = n01(gauss(hue * satn, 1.0))
            smf = float(sm)
            # MACRO CLEARCOAT: Cc carved primarily from the blocky macro
            # domain map -> env-reflection travel sweeps the car in big
            # coherent cells, not uniform micro shimmer. Hue domains remain
            # as accent for channel decorrelation.
            _, _dd = self.macro_cached(fid)
            domw = cv2.resize(_dd, (WORK, WORK), interpolation=cv2.INTER_NEAREST)
            hfield = n01(0.72 * domw + 0.28 * hdom)
            rkw = self.ALL[fid].get("kw", {})
            msw = float(rkw.get("mswing", 1.0))
            rsw = float(rkw.get("rswing", 1.0))
            # ccpat: for heavily gray-dialed (low-chroma) recipes the hue
            # domains are too weak to carve clearcoat travel — blend the luma
            # relief back in.
            ccp = float(rkw.get("ccpat", 0.0))
            cfield = hfield * (1.0 - ccp) + pattern * ccp if ccp > 0.0 else hfield
            mfl = float(rkw.get("mfloor", 40.0))
            ccb = float(rkw.get("ccboost", 1.0))
            rcl = float(rkw.get("rceil", 195.0))
            # THE GHOST-SHIFT CONTRACT (owner-proven dials):
            #   METAL = the color amplifier; swings from the SAME art.
            M = np.clip(215.0 + ((micro - 0.5) * 320.0 + edge * 128.0 - (1.0 - pattern) * 96.0) * msw, mfl, 255.0)
            #   ROUGHNESS = the angular aperture: lane-driven, wider travel.
            lane = np.clip((pattern * 0.85 + edge * 0.75 - 0.42) * 1.9, 0.0, 1.0)
            R = np.clip(18.0 + (150.0 * lane + (micro - 0.5) * 40.0 - edge * 12.0) * rsw, 6.0, rcl)
            #   CLEARCOAT = the power supply, carved by the hue/macro domains.
            Cc = np.clip(224.0 - cfield * 190.0 * ccb + micro * 22.0, 16.0, 255.0)
            out = np.zeros((WORK, WORK, 4), np.uint8)
            mk = np.clip(m2, 0.0, 1.0)
            inv = 1.0 - mk
            out[:, :, 0] = np.clip(M * mk + 4.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 1] = np.clip(R * mk + 120.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 2] = np.clip(Cc * mk + 16.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 3] = 255
            if (fh, fw) != (WORK, WORK):
                out = cv2.resize(out, (fw, fh), interpolation=cv2.INTER_LINEAR)
            return out

        return spec_fn, paint_fn

    # ════════════════════════════════════════════════════════════════════

    def install_into_engine(self, mono_reg, base_reg=None):
        """Register every finish of this category into the monolithic + fusion
        registries (mirrors fractured_themes_2026.install_into_engine)."""
        regs = [mono_reg]
        try:
            import engine.expansions.fusions as _fus
            regs.append(_fus.FUSION_REGISTRY)
        except Exception:
            pass
        import sys as _sys
        _eng = _sys.modules.get("shokker_engine_v2")
        if _eng is not None and hasattr(_eng, "FUSION_REGISTRY"):
            regs.append(_eng.FUSION_REGISTRY)
        n = 0
        for fid in self.ALL:
            entry = self.mk(fid)
            for reg in regs:
                reg[fid] = entry
            n += 1
        counts = ", ".join(f"{g}:{len(d)}" for g, d in self.GROUPS.items())
        return f"{self.tag}: {n} finishes live ({counts})"
