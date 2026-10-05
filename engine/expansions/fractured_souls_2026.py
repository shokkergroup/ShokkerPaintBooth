# -*- coding: utf-8 -*-
"""FRACTURED SOULS (2026-06-12) — the apex of the Ghost Fracture experiment.

Built directly from the owner's LIVE slider lab on Ghost Fracture (the
four-dial physics, proven on track):

  CLEARCOAT (B) = the POWER SUPPLY. Max it (~246) and color fires through.
  ROUGHNESS (G) = the angular APERTURE of the reveal:
        ~0-25  -> needle "laser pin" glints dancing with sun angle
        ~45-90 -> wide window: whole DESIGNS flash through at the magic angle
        >120   -> closed. Flat. Dead. (This is why high-G pastel looked
                  pretty in thumbnails and would die on track.)
  METAL (R)     = the COLOR AMPLIFIER. Keep near max (~242); dropping it
                  brightens the car and kills the magic.
  PAINT VALUE   = the COLOR MIXER. Pre-crushed dark (~0.10-0.18) is the
                  sweet spot: color blasts through reveals while the car
                  still reads matte black.

DRAG-AND-DROP CONTRACT: no sliders needed. The paint ships PRE-CRUSHED, the
spec ships at the proven dial values. 5 textureless SOUL CORES (pure color
morphing) + 10 textured offshoots whose DESIGN lives mostly in the
ROUGHNESS channel — aperture lanes that reveal the motif at angle, exactly
like the owner's Forbidden Dragon G-sweep discovery.
"""
import numpy as np
import cv2

from engine.expansions.redesign_wave2_2026 import (
    _rng, _noise, _n01, _sstep, _gauss, _coords, _warp, _curves, _dendrites,
    _flow_theta, _flowlines, _crystal, _harmonograph, _seed_int, _sr,
)

_WORKS = 1024
_FS_CACHE = {}

# The proven contract (owner lab values, GF baseline + best dials)
SOUL_M = 242.0          # metal near max — the color amplifier
SOUL_G = 30.0           # ultra-gloss floor — laser-pin aperture
SOUL_G_LANE = 78.0      # textured lanes — wide design-reveal aperture
SOUL_B = 246.0          # clearcoat power supply

SOULS = {}


def _def(fid):
    def deco(builder):
        SOULS[fid] = builder()
        return builder
    return deco


def _fs_fields(fid, h, w, s):
    key = (fid, h, w, s)
    if key in _FS_CACHE:
        return _FS_CACHE[key]
    if len(_FS_CACHE) > 5:
        _FS_CACHE.pop(next(iter(_FS_CACHE)))
    out = SOULS[fid]["fields"](h, w, s)
    _FS_CACHE[key] = out
    return out


def _core(color):
    """A textureless SOUL CORE: pure contract spec + flat pre-crushed paint."""
    col = np.float32(color)

    def fields(h, w, s):
        return (np.zeros((h, w), np.float32),)

    def spec(F, s, h, w):
        z = F[0]
        M = np.full_like(z, SOUL_M)
        G = np.full_like(z, SOUL_G)
        B = np.full_like(z, SOUL_B)
        return M, G, B

    def paint(F, src_lum):
        z = F[0]
        art = np.empty((z.shape[0], z.shape[1], 3), np.float32)
        art[:] = col[None, None, :]
        k = np.full_like(z, 0.92)          # the core IS the color — own it
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint, "core": True}


# ───────────────────────── THE FIVE SOUL CORES ─────────────────────────────
# Pre-crushed at the owner's sweet spot: dark enough to read matte black-ish,
# bright enough that the reveal carries the hue.
SOULS["fs_core_violet"] = _core((0.11, 0.05, 0.18))
# [round-2 owner lab finding: the flash reads as the COMPLEMENT of the base,
# and the daytime env palette lives on the gold<->teal axis — bases sitting ON
# that axis (pure blue r68, pure red r47) camouflage their own flash. Both
# rebuilt OFF-axis: abyss -> indigo-violet lean, crimson -> magenta-rose lean.]
SOULS["fs_core_abyss"] = _core((0.07, 0.05, 0.22))
SOULS["fs_core_emerald"] = _core((0.04, 0.16, 0.09))
SOULS["fs_core_crimson"] = _core((0.19, 0.03, 0.11))
SOULS["fs_core_aurum"] = _core((0.20, 0.15, 0.03))


# ─────────────────────── TEN TEXTURED OFFSHOOTS ────────────────────────────
# Same physics; the MOTIF lives in the ROUGHNESS channel as aperture lanes
# (G ~78 = wide reveal window) over the ultra-gloss pin floor (G ~30), with
# small clearcoat/metal seasoning. Paints ship pre-crushed with faint texture.

def _soul_spec(lane, pins=None, m_tex=None, b_tex=None):
    """Shared CONTRACT assembly — deliberately identical physics per the
    owner ('EXACT same principle, different textures/designs')."""
    lane = np.asarray(lane, np.float32)
    M = np.zeros_like(lane) + SOUL_M + (m_tex if m_tex is not None else 0.0)
    G = SOUL_G + (SOUL_G_LANE - SOUL_G) * lane
    if pins is not None:
        G = G * (1.0 - pins) + 14.0 * pins        # glitter pins: razor aperture
    B = np.zeros_like(lane) + SOUL_B + (b_tex if b_tex is not None else 0.0)
    return (np.clip(M, 0, 255), np.clip(G, 14, 110), np.clip(B, 225, 252))


def _soul_paint(base_col, art_fields, k_extra=0.0):
    col = np.float32(base_col)
    art = np.empty((art_fields.shape[0], art_fields.shape[1], 3), np.float32)
    art[:] = col[None, None, :]
    art *= (0.75 + 0.5 * art_fields)[..., None]   # faint value texture only
    return np.clip(art, 0, 1), np.clip(0.88 + k_extra * art_fields, 0, 1)


@_def("fs_wraith_veil")  # smoky flowing veils — purple
def _b_wraith():
    def fields(h, w, s):
        sr = _sr(h, w)
        flow = _noise(h, w, s, (24, 60, 140))
        veil = _sstep(0.42, 0.62, np.abs(np.sin(flow * 9.0)))
        wisps = _n01(_noise(h, w, s ^ 0x21, (8, 18)))
        return veil.astype(np.float32), wisps

    def spec(F, s, h, w):
        veil, wisps = F
        return _soul_spec(veil, m_tex=6 * (wisps - 0.5), b_tex=4 * (veil - 0.5))

    def paint(F, src_lum):
        veil, wisps = F
        return _soul_paint((0.11, 0.05, 0.18), veil * 0.7 + wisps * 0.3)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_moth_dust")  # glitter field — gold
def _b_mothdust():
    def fields(h, w, s):
        sr = _sr(h, w)
        pins = _sstep(0.90, 0.965, _noise(h, w, s, (1.8, 3.5)))
        dust = _sstep(0.55, 0.85, _noise(h, w, s ^ 0x31, (4, 9)))
        return pins.astype(np.float32), dust

    def spec(F, s, h, w):
        pins, dust = F
        return _soul_spec(dust * 0.45, pins=pins, b_tex=5 * pins)

    def paint(F, src_lum):
        pins, dust = F
        return _soul_paint((0.20, 0.15, 0.03), dust * 0.5 + pins)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_blood_marble")  # marbled horror swirls — crimson
def _b_bloodmarble():
    def fields(h, w, s):
        sr = _sr(h, w)
        yy, xx = _coords(h, w)
        yy2, xx2 = _warp(yy, xx, h, w, s, 26 * sr)
        vein = 1.0 - np.abs(np.sin((xx2 + yy2 * 0.6) * 2 * np.pi / (38 * sr)))
        marble = _sstep(0.80, 0.94, vein)
        grain = _n01(_noise(h, w, s ^ 0x41, (6, 14)))
        return marble.astype(np.float32), grain

    def spec(F, s, h, w):
        marble, grain = F
        # owner's winning dial state recovered from render 2026-06-12 18:23
        # (forensic per-pixel diff vs no-dial baseline): metal +10 on every
        # pixel, roughness untouched, clearcoat railed flat at 255 — the
        # marble carve in B is intentionally gone (B-rail IS the magic).
        M, G, _B = _soul_spec(marble, m_tex=10.0 + 5 * (grain - 0.5))
        B = np.zeros_like(M) + 255.0
        return M, G, B

    def paint(F, src_lum):
        marble, grain = F
        return _soul_paint((0.18, 0.04, 0.06), marble * 0.8 + grain * 0.2)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_night_tide")  # rolling wave caustic lanes — abyss blue
def _b_nighttide():
    def fields(h, w, s):
        sr = _sr(h, w)
        r1 = 1.0 - np.abs(_noise(h, w, s, (16, 36)) * 2 - 1)
        lanes = _sstep(0.72, 0.90, r1)
        swell = _n01(_noise(h, w, s ^ 0x51, (90, 220)))
        return lanes.astype(np.float32), swell

    def spec(F, s, h, w):
        lanes, swell = F
        return _soul_spec(lanes, m_tex=4 * (swell - 0.5), b_tex=4 * lanes)

    def paint(F, src_lum):
        lanes, swell = F
        return _soul_paint((0.04, 0.07, 0.20), lanes * 0.6 + swell * 0.4)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_static_veins")  # electric filaments — emerald
def _b_staticveins():
    def fields(h, w, s):
        sr = _sr(h, w)
        fil = _dendrites(h, w, s, n_roots=900, depth=4, seg=12 * sr, thick=1)
        halo = np.clip(_gauss(fil, 1.6 * sr) * 2.4, 0, 1)
        return halo.astype(np.float32), fil.astype(np.float32)

    def spec(F, s, h, w):
        halo, fil = F
        return _soul_spec(halo, pins=fil, b_tex=4 * fil)

    def paint(F, src_lum):
        halo, fil = F
        return _soul_paint((0.04, 0.16, 0.09), halo * 0.6 + fil * 0.4)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_shatter_glass")  # angular shard lanes — ice violet
def _b_shatterglass():
    def fields(h, w, s):
        sr = _sr(h, w)
        cid, edge, orient, axial = _crystal(h, w, s, n_sites=900, aniso=2.2, res=0.5)
        cracks = 1.0 - _sstep(0.03, 0.09, edge)
        per = _n01(np.sin(cid * 12.99) + 1)
        shard = _sstep(0.62, 0.68, per)
        return np.clip(cracks + shard * 0.6, 0, 1).astype(np.float32), shard

    def spec(F, s, h, w):
        lanes, shard = F
        return _soul_spec(lanes, b_tex=4 * shard - 2)

    def paint(F, src_lum):
        lanes, shard = F
        return _soul_paint((0.10, 0.07, 0.19), lanes * 0.5 + shard * 0.5)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_howl")  # radial scratch flares (horror) — ash violet
def _b_howl():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 13)
        canvas = np.zeros((h, w), np.uint8)
        for _ in range(int(260 * sr * sr) + 50):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            a = rng.uniform(0, 2 * np.pi)
            L = rng.uniform(14, 42) * sr
            for k in range(3):
                aa = a + rng.uniform(-0.16, 0.16)
                cv2.line(canvas, (int(cx), int(cy)),
                         (int(cx + np.cos(aa) * L), int(cy + np.sin(aa) * L)), 255, 1)
        scratch = (canvas > 0).astype(np.float32)
        flare = np.clip(_gauss(scratch, 2.2 * sr) * 2.2, 0, 1)
        return flare.astype(np.float32), scratch

    def spec(F, s, h, w):
        flare, scratch = F
        return _soul_spec(flare, pins=scratch, b_tex=3 * scratch)

    def paint(F, src_lum):
        flare, scratch = F
        return _soul_paint((0.12, 0.09, 0.14), flare * 0.7 + scratch * 0.3)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_phantom_lattice")  # faint diamond lattice — gunmetal teal
def _b_phantomlattice():
    def fields(h, w, s):
        sr = _sr(h, w)
        yy, xx = _coords(h, w)
        a = float(_rng(s, 3).uniform(0, np.pi))
        u = xx * np.cos(a) + yy * np.sin(a)
        v = -xx * np.sin(a) + yy * np.cos(a)
        p = 11.0 * sr
        d1 = np.abs(((u + v) / p) - np.round((u + v) / p))
        d2 = np.abs(((u - v) / p) - np.round((u - v) / p))
        lattice = 1.0 - _sstep(0.05, 0.16, np.minimum(d1, d2))
        weave = _n01(_noise(h, w, s ^ 0x71, (40, 110)))
        return lattice.astype(np.float32), weave

    def spec(F, s, h, w):
        lattice, weave = F
        return _soul_spec(lattice, m_tex=4 * (weave - 0.5))

    def paint(F, src_lum):
        lattice, weave = F
        return _soul_paint((0.05, 0.13, 0.15), lattice * 0.6 + weave * 0.4)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_ember_drift")  # round-2 rebuild (owner r35: "too big, lazy, need
# COLOR in the paint channel even crushed") — a dense fine ember rain: many
# short tapered streaks at all angles, three crushed fire hues in the paint.
def _b_emberdrift():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 31)
        canvas = np.zeros((h, w), np.uint8)
        hot = np.zeros((h, w), np.uint8)
        for _ in range(int(5200 * sr * sr) + 600):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            a = rng.uniform(0, 2 * np.pi)
            L = rng.uniform(3.0, 9.0) * sr
            x2, y2 = cx + np.cos(a) * L, cy + np.sin(a) * L
            cv2.line(canvas, (int(cx), int(cy)), (int(x2), int(y2)), 255, 1)
            if rng.uniform(0, 1) < 0.30:
                cv2.circle(hot, (int(x2), int(y2)), max(1, int(0.8 * sr)), 255, -1)
        streak = (canvas > 0).astype(np.float32)
        sparks = (hot > 0).astype(np.float32)
        lanes = np.clip(_gauss(streak, 1.4 * sr) * 2.2, 0, 1)
        heat = _n01(_noise(h, w, s ^ 0x61, (40, 110)))
        return lanes.astype(np.float32), streak, sparks, heat

    def spec(F, s, h, w):
        lanes, streak, sparks, heat = F
        return _soul_spec(lanes, pins=np.clip(streak + sparks, 0, 1), b_tex=4 * sparks)

    def paint(F, src_lum):
        lanes, streak, sparks, heat = F
        # three crushed fire hues — color LIVES in the paint channel even
        # though it ships dark (owner note)
        deep = np.float32((0.14, 0.03, 0.02))
        ember = np.float32((0.22, 0.09, 0.02))
        gold = np.float32((0.24, 0.16, 0.04))
        art = np.empty((lanes.shape[0], lanes.shape[1], 3), np.float32)
        art[:] = deep[None, None, :]
        art = art * (1 - lanes[..., None]) + ember[None, None, :] * lanes[..., None]
        art = art * (1 - sparks[..., None]) + gold[None, None, :] * sparks[..., None]
        art *= (0.8 + 0.4 * heat)[..., None]
        return np.clip(art, 0, 1), np.full_like(lanes, 0.9)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_carnival_night")  # confetti pin swarm — midnight multi
def _b_carnival():
    def fields(h, w, s):
        sr = _sr(h, w)
        # owner overnight fix 2026-06-13: confetti was ~0.1% coverage (read DEAD
        # flat even at 2048) — denser + finer pins so the swarm actually shows
        c1 = _sstep(0.76, 0.88, _noise(h, w, s, (2.0, 4.0)))
        c2 = _sstep(0.78, 0.90, _noise(h, w, s ^ 0x91, (2.3, 4.6)))
        c3 = _sstep(0.80, 0.92, _noise(h, w, s ^ 0x92, (2.6, 5.2)))
        field = _n01(_noise(h, w, s ^ 0x93, (30, 80)))
        return c1.astype(np.float32), c2.astype(np.float32), c3.astype(np.float32), field

    def spec(F, s, h, w):
        c1, c2, c3, field = F
        pins = np.clip(c1 + c2 + c3, 0, 1)
        return _soul_spec(field * 0.4, pins=pins, b_tex=4 * pins)

    def paint(F, src_lum):
        c1, c2, c3, field = F
        base = np.float32((0.07, 0.06, 0.14))
        art = np.empty((field.shape[0], field.shape[1], 3), np.float32)
        art[:] = base[None, None, :]
        art += np.float32((0.42, 0.07, 0.14))[None, None, :] * c1[..., None]
        art += np.float32((0.06, 0.30, 0.34))[None, None, :] * c2[..., None]
        art += np.float32((0.34, 0.27, 0.03))[None, None, :] * c3[..., None]
        return np.clip(art, 0, 1), np.full_like(field, 0.9)

    return {"fields": fields, "spec": spec, "paint": paint}


# ═══════════════════════ ROUND 3 (2026-06-12): 15 NEW SOULS ═══════════════════
# Owner mandate: expand to 30. A few take liberties with WOVENLIGHT's
# construction (the warped two-axis ribbon weave / parity / thread striations /
# third-angle sheen). Everything ships on the WINNER physics recovered from the
# owner's Blood Marble forensics: M ~252 (amplifier +10), B railed flat 255
# (the power-supply rail IS the magic), G = floor 30 + fine design lanes.
# Fine detail everywhere — no blotch. Multi-hue crushed paints so that many
# colors pop through at angle ("47 colors popping through").

SOUL_M2 = 252.0     # winner-recovered amplifier rail (Blood Marble bake)


def _soul_spec_v2(lane, pins=None, m_tex=None):
    """Winner contract: B flat 255, M ~252 (+/- design micro), G aperture lanes."""
    lane = np.asarray(lane, np.float32)
    M = np.zeros_like(lane) + SOUL_M2 + (m_tex if m_tex is not None else 0.0)
    G = SOUL_G + (SOUL_G_LANE - SOUL_G) * lane
    if pins is not None:
        G = G * (1.0 - pins) + 14.0 * pins
    B = np.zeros_like(lane) + 255.0
    return (np.clip(M, 0, 255), np.clip(G, 14, 110), B)


def _hsv_field(hue, sat, val):
    """Vectorized HSV->RGB (all args scalar or (h,w)); returns (h,w,3) float32."""
    hue, sat, val = np.broadcast_arrays(
        np.asarray(hue, np.float32) % 1.0,
        np.asarray(sat, np.float32), np.asarray(val, np.float32))
    h6 = hue * 6.0
    i = np.floor(h6).astype(np.int32) % 6
    f = (h6 - np.floor(h6)).astype(np.float32)
    p = val * (1 - sat); q = val * (1 - sat * f); t = val * (1 - sat * (1 - f))
    r = np.choose(i, [val, q, p, p, t, val])
    g = np.choose(i, [t, val, val, q, p, p])
    b = np.choose(i, [p, p, t, val, val, q])
    return np.stack([r, g, b], -1).astype(np.float32)


def _frac(a):
    a = np.asarray(a, np.float32)
    return (a - np.floor(a)).astype(np.float32)


@_def("fs_soul_loom")  # WOVENLIGHT TWIST 1 — the loom itself, crushed.
# Two warped ribbon axes, parity over/under, grooves, dive shadows, thread
# striations — but finer pitch than Wovenlight and pre-crushed emerald x
# violet so the WEAVE flashes two colors by sun angle.
def _b_soulloom():
    def fields(h, w, s):
        sr = _sr(h, w)
        yy, xx = _coords(h, w)
        rng = _rng(s, 5)
        a1 = float(rng.uniform(0, np.pi))
        a2 = a1 + 0.5 * np.pi + float(rng.uniform(-0.18, 0.18))
        p1 = max(8.0, float(rng.uniform(20.0, 27.0)) * sr)
        p2 = max(8.0, float(rng.uniform(23.0, 31.0)) * sr)
        wu = (_noise(h, w, s ^ 0xA1, (40, 110)) - 0.5) * (8.0 * sr)
        wv = (_noise(h, w, s ^ 0xA2, (46, 120)) - 0.5) * (8.0 * sr)
        u = (xx * np.cos(a1) + yy * np.sin(a1) + wu) / p1
        v = (xx * np.cos(a2) + yy * np.sin(a2) + wv) / p2
        iu, iv = np.floor(u), np.floor(v)
        fu, fv = (u - iu).astype(np.float32), (v - iv).astype(np.float32)
        parity = ((iu + iv) % 2.0).astype(np.float32)
        warp_top = (1.0 - parity).astype(np.float32)
        prof_u = np.sin(np.pi * fu).astype(np.float32)
        prof_v = np.sin(np.pi * fv).astype(np.float32)
        eu = np.minimum(fu, 1 - fu); ev = np.minimum(fv, 1 - fv)
        groove = (1.0 - np.clip(np.minimum(eu, ev) / 0.06, 0, 1)).astype(np.float32)
        corridor = np.maximum(1.0 - np.clip(eu / 0.26, 0, 1),
                              1.0 - np.clip(ev / 0.26, 0, 1)).astype(np.float32)
        n1 = float(rng.integers(7, 10)); n2 = float(rng.integers(7, 10))
        thread = (warp_top * (0.5 + 0.5 * np.cos(2 * np.pi * fu * n1)) +
                  parity * (0.5 + 0.5 * np.cos(2 * np.pi * fv * n2))).astype(np.float32)
        dive = (warp_top * (1 - np.clip(ev / 0.32, 0, 1)) +
                parity * (1 - np.clip(eu / 0.32, 0, 1))).astype(np.float32)
        return warp_top, parity, prof_u, prof_v, groove, corridor, thread, dive

    def spec(F, s, h, w):
        wt, par, pu, pv, gr, cor, th, dv = F
        rib = np.maximum(pu * wt, pv * par)
        lane = np.clip(0.9 * cor + 0.5 * th * (0.35 + 0.65 * rib) - 0.5 * gr, 0, 1)
        return _soul_spec_v2(lane, m_tex=7 * (th - 0.5) - 6 * gr)

    def paint(F, src_lum):
        wt, par, pu, pv, gr, cor, th, dv = F
        emerald = np.float32((0.035, 0.150, 0.080))
        violet = np.float32((0.130, 0.045, 0.200))
        bw = (0.45 + 0.75 * pu * (0.8 + 0.2 * th))[..., None]
        bf = (0.45 + 0.75 * pv * (0.8 + 0.2 * th))[..., None]
        art = emerald[None, None, :] * bw * wt[..., None] + \
            violet[None, None, :] * bf * par[..., None]
        shade = (1.0 - 0.40 * dv) * (1.0 - 0.55 * gr)
        art = np.clip(art * shade[..., None], 0, 1)
        return art, np.full(wt.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_widow_braid")  # WOVENLIGHT TWIST 2 — tri-axial braid.
# Three warped strand families 60 degrees apart; the on-top family cycles like
# a braid. THREE crushed hues, so the weave flashes a different color from
# three different sun geometries.
def _b_widowbraid():
    def fields(h, w, s):
        sr = _sr(h, w)
        yy, xx = _coords(h, w)
        rng = _rng(s, 7)
        a0 = float(rng.uniform(0, np.pi))
        p = max(8.0, float(rng.uniform(19.0, 25.0)) * sr)
        us, fr, prof = [], [], []
        for k in range(3):
            a = a0 + k * (np.pi / 3.0)
            wk = (_noise(h, w, s ^ (0xB1 + k), (38, 100)) - 0.5) * (7.0 * sr)
            u = (xx * np.cos(a) + yy * np.sin(a) + wk) / p
            us.append(np.floor(u)); fr.append((u - np.floor(u)).astype(np.float32))
            prof.append(np.sin(np.pi * fr[-1]).astype(np.float32))
        cyc = ((us[0] + us[1] + us[2]) % 3.0).astype(np.float32)
        tops = [(cyc == k).astype(np.float32) for k in range(3)]
        thread = np.zeros((h, w), np.float32)
        edge = np.zeros((h, w), np.float32)
        for k in range(3):
            ek = np.minimum(fr[k], 1 - fr[k])
            thread += tops[k] * (0.5 + 0.5 * np.cos(2 * np.pi * fr[k] * 8.0))
            edge = np.maximum(edge, tops[k] * (1.0 - np.clip(ek / 0.10, 0, 1)))
        cross = np.maximum.reduce([1.0 - np.clip(np.minimum(fr[k], 1 - fr[k]) / 0.22, 0, 1)
                                   for k in range(3)])
        topprof = tops[0] * prof[0] + tops[1] * prof[1] + tops[2] * prof[2]
        return tops[0], tops[1], tops[2], topprof, thread.astype(np.float32), \
            edge.astype(np.float32), cross.astype(np.float32)

    def spec(F, s, h, w):
        t0, t1, t2, tp, th, ed, cr = F
        lane = np.clip(0.85 * cr + 0.5 * th * (0.3 + 0.7 * tp) - 0.45 * ed, 0, 1)
        return _soul_spec_v2(lane, m_tex=7 * (th - 0.5) - 5 * ed)

    def paint(F, src_lum):
        t0, t1, t2, tp, th, ed, cr = F
        rose = np.float32((0.180, 0.035, 0.110))
        petrol = np.float32((0.020, 0.110, 0.130))
        amber = np.float32((0.180, 0.115, 0.025))
        b = (0.45 + 0.75 * tp * (0.8 + 0.2 * th))[..., None]
        art = (rose[None, None, :] * t0[..., None] + petrol[None, None, :] * t1[..., None]
               + amber[None, None, :] * t2[..., None]) * b
        art = np.clip(art * (1.0 - 0.50 * ed)[..., None], 0, 1)
        return art, np.full(tp.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_ghost_silk")  # WOVENLIGHT TWIST 3 — the thread striations alone.
# Micro satin threads (3-4px) gated by slow satin patches, with Wovenlight's
# third-angle sheen pools deciding WHERE the silk ignites; hue slides
# indigo<->teal along the sheen so the shimmer changes color as it travels.
def _b_ghostsilk():
    def fields(h, w, s):
        sr = _sr(h, w)
        yy, xx = _coords(h, w)
        rng = _rng(s, 9)
        a1 = float(rng.uniform(0, np.pi))
        p1 = max(3.2, 5.2 * sr)
        wu = (_noise(h, w, s ^ 0xC1, (30, 80)) - 0.5) * (10.0 * sr)
        u = (xx * np.cos(a1) + yy * np.sin(a1) + wu) / p1
        thread = (0.5 + 0.5 * np.cos(2 * np.pi * u)).astype(np.float32) ** 3.0
        # mid-scale streak bundles along the SAME axis so the silk reads as
        # directional strands (not clouds) even from distance
        bundle = (0.5 + 0.5 * np.cos(2 * np.pi * u / 4.7)).astype(np.float32)
        thread = thread * (0.45 + 0.55 * _sstep(0.25, 0.75, bundle))
        # crisp satin panels, not soft clouds (owner: nothing blotchy)
        gate = _sstep(0.44, 0.60, _noise(h, w, s ^ 0xC2, (60, 160)))
        a3 = a1 + float(rng.uniform(0.5, 1.1))
        p3 = max(40.0, float(rng.uniform(150.0, 220.0)) * sr)
        w3 = (_noise(h, w, s ^ 0xC3, (64, 170)) - 0.5) * (36.0 * sr)
        c3 = (xx * np.cos(a3) + yy * np.sin(a3) + w3) / p3
        sheen = ((0.5 + 0.5 * np.sin(2 * np.pi * c3)) ** 2.0).astype(np.float32)
        return thread.astype(np.float32), gate.astype(np.float32), sheen

    def spec(F, s, h, w):
        thread, gate, sheen = F
        lane = np.clip(thread * (0.30 + 0.70 * gate) * (0.40 + 0.60 * sheen) * 1.25, 0, 1)
        return _soul_spec_v2(lane, m_tex=6 * (gate - 0.5))

    def paint(F, src_lum):
        thread, gate, sheen = F
        hue = 0.58 + 0.14 * sheen - 0.05 * gate          # indigo -> teal slide
        val = 0.050 + 0.190 * thread * (0.30 + 0.70 * gate)
        art = _hsv_field(hue, 0.82, val)
        return art, np.full(thread.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_shattered_prism")  # the "47 colors" flagship — fine crystal mosaic,
# EVERY cell its own crushed hue; borders + per-cell facet striations carve the
# aperture so each cell pops its own complement at its own angle.
def _b_shatteredprism():
    def fields(h, w, s):
        sr = _sr(h, w)
        n = int(2400 * sr * sr) + 220
        cid, edge, orient, axial = _crystal(h, w, s, n_sites=n, aniso=1.7, res=0.5)
        borders = (1.0 - _sstep(0.05, 0.13, edge)).astype(np.float32)
        cf = cid.astype(np.float32)
        hue = _frac(cf * 0.6180339887)
        h2 = _frac(cf * 0.7548776662)
        h3 = _frac(cf * 0.5698402910)
        fa = (0.5 + 0.5 * np.cos(axial * 2 * np.pi / (5.0 * sr))).astype(np.float32)
        facet = _sstep(0.62, 0.86, fa) * _sstep(0.55, 0.62, h2)   # only some cells striate
        return borders, hue, h2, h3, facet

    def spec(F, s, h, w):
        borders, hue, h2, h3, facet = F
        lane = np.clip(0.95 * borders + 0.55 * facet, 0, 1)
        return _soul_spec_v2(lane, m_tex=10 * (h3 - 0.5))

    def paint(F, src_lum):
        borders, hue, h2, h3, facet = F
        val = 0.055 + 0.150 * h2
        art = _hsv_field(hue, 0.85, val)
        art = np.clip(art * (1.0 - 0.55 * borders)[..., None], 0, 1)
        return art, np.full(borders.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_oil_serpent")  # advected serpent currents; the strand color follows
# the FLOW DIRECTION (direction-indexed hue), so the same paint flashes
# magenta, gold and teal depending on which way the current bends.
def _b_oilserpent():
    def fields(h, w, s):
        sr = _sr(h, w)
        theta = _flow_theta(h, w, s, scale=150.0, turns=2.2, swirls=3)
        lines = _flowlines(h, w, s, n=int(1500 * sr * sr) + 220, steps=90,
                           step_len=2.0, theta=theta, thick=1, fade=True)
        halo = np.clip(_gauss(lines, 2.0 * sr) * 1.8, 0, 1)
        return lines.astype(np.float32), halo.astype(np.float32), \
            theta.astype(np.float32)

    def spec(F, s, h, w):
        lines, halo, theta = F
        lane = np.clip(0.85 * halo + 0.55 * lines, 0, 1)
        return _soul_spec_v2(lane, m_tex=6 * (halo - 0.5))

    def paint(F, src_lum):
        lines, halo, theta = F
        hue = _frac(0.46 + 0.22 * np.sin(theta))          # petrol wheel
        val = 0.050 + (0.085 * halo + 0.125 * lines)
        art = _hsv_field(hue, 0.82, val)
        return art, np.full(lines.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_hex_hive")  # dead hive — fine rotated honeycomb, three crushed hues
# cycling cell-by-cell, walls carve the aperture, a pore pin in every cell.
def _b_hexhive():
    def fields(h, w, s):
        sr = _sr(h, w)
        yy, xx = _coords(h, w)
        rng = _rng(s, 11)
        a = float(rng.uniform(0, np.pi))
        size = max(5.0, 7.5 * sr)
        wx = (_noise(h, w, s ^ 0xD1, (50, 130)) - 0.5) * (5.0 * sr)
        wy = (_noise(h, w, s ^ 0xD2, (55, 140)) - 0.5) * (5.0 * sr)
        x = (xx * np.cos(a) + yy * np.sin(a) + wx) / size
        y = (-xx * np.sin(a) + yy * np.cos(a) + wy) / size
        q = (np.sqrt(3.0) / 3.0 * x - y / 3.0)
        r = (2.0 / 3.0 * y)
        cz = -q - r
        rq, rr, rz = np.round(q), np.round(r), np.round(cz)
        dq, dr, dz = np.abs(rq - q), np.abs(rr - r), np.abs(rz - cz)
        fixq = (dq > dr) & (dq > dz)
        fixr = (~fixq) & (dr > dz)
        rq = np.where(fixq, -rr - rz, rq)
        rr = np.where(fixr, -rq - rz, rr)
        # distance to cell center in hex space -> walls + pore
        cx = np.sqrt(3.0) * (rq + rr / 2.0)
        cy = 1.5 * rr
        px = np.sqrt(3.0) * (q + r / 2.0)
        py = 1.5 * r
        d = np.sqrt((px - cx) ** 2 + (py - cy) ** 2).astype(np.float32)
        walls = _sstep(0.70, 0.86, d)
        pore = (1.0 - _sstep(0.10, 0.22, d)).astype(np.float32)
        cellk = ((rq + 2.0 * rr) % 3.0).astype(np.float32)
        chash = _frac(rq * 0.61803 + rr * 0.75487)
        return walls.astype(np.float32), pore, cellk, chash.astype(np.float32)

    def spec(F, s, h, w):
        walls, pore, cellk, chash = F
        lane = np.clip(0.9 * walls + 0.35 * _sstep(0.6, 0.9, chash), 0, 1)
        return _soul_spec_v2(lane, pins=pore, m_tex=8 * (chash - 0.5))

    def paint(F, src_lum):
        walls, pore, cellk, chash = F
        amber = np.float32((0.200, 0.120, 0.025))
        umber = np.float32((0.085, 0.050, 0.020))
        petrol = np.float32((0.025, 0.105, 0.120))
        art = (amber[None, None, :] * (cellk == 0)[..., None]
               + umber[None, None, :] * (cellk == 1)[..., None]
               + petrol[None, None, :] * (cellk == 2)[..., None]).astype(np.float32)
        art *= (0.70 + 0.45 * chash)[..., None]
        art = np.clip(art * (1.0 - 0.55 * walls)[..., None], 0, 1)
        return art, np.full(walls.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_guilloche_ghost")  # banknote engine-turning — two interleaved
# harmonograph rosette grids, hairline curves only; crossings pin razor glints.
def _b_guillocheghost():
    def fields(h, w, s):
        sr = _sr(h, w)
        # true engine-turning: LARGE overlapping rosette nets whose individual
        # curves stay hairline-fine (small-cell versions read as stamped coins)
        g1 = _harmonograph(h, w, s, cells=max(3, int(4 * sr)), m=5200, pens=2,
                           decay=0.30, thick=1, jitter=0.20)
        g2 = _harmonograph(h, w, s ^ 0xE7, cells=max(4, int(6 * sr)), m=3600,
                           pens=1, decay=0.26, thick=1, jitter=0.22)
        g2 = np.maximum(g2, _harmonograph(h, w, s ^ 0x3B9, cells=max(4, int(5 * sr)),
                                          m=3000, pens=1, decay=0.24, thick=1,
                                          jitter=0.46))
        cross = np.clip(g1 * g2 * 4.0, 0, 1)
        return g1.astype(np.float32), g2.astype(np.float32), cross.astype(np.float32)

    def spec(F, s, h, w):
        g1, g2, cross = F
        # open hairline spirals — gains kept low so dense rosettes never
        # saturate into solid aperture pools
        lane = np.clip(0.80 * g1 + 0.55 * g2, 0, 1)
        return _soul_spec_v2(lane, pins=_sstep(0.5, 0.9, cross),
                             m_tex=5 * (np.clip(g1 + g2, 0, 1) - 0.5))

    def paint(F, src_lum):
        g1, g2, cross = F
        base = np.float32((0.110, 0.075, 0.030))           # crushed bronze
        champ = np.float32((0.230, 0.185, 0.090))
        teal = np.float32((0.030, 0.110, 0.120))
        art = np.empty(g1.shape + (3,), np.float32)
        art[:] = base[None, None, :] * 0.55
        art = art * (1 - g1[..., None]) + champ[None, None, :] * g1[..., None]
        art = art * (1 - g2[..., None] * 0.8) + teal[None, None, :] * (g2 * 0.8)[..., None]
        return np.clip(art, 0, 1), np.full(g1.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_petrol_halo")  # Newton-ring packets — scattered interference halos,
# fine concentric rings whose hue cycles with ring index (oil-on-water).
def _b_petrolhalo():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 13)
        rings = np.zeros((h, w), np.float32)
        huef = np.zeros((h, w), np.float32)
        env_best = np.zeros((h, w), np.float32)
        n = int(55 * sr * sr) + 18
        for i in range(n):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            R = rng.uniform(65, 130) * sr
            pitch = rng.uniform(4.5, 7.0) * sr
            ph = rng.uniform(0, 2 * np.pi)
            hb = rng.uniform(0, 1)
            x0, x1 = int(max(0, cx - R)), int(min(w, cx + R + 1))
            y0, y1 = int(max(0, cy - R)), int(min(h, cy + R + 1))
            if x1 <= x0 or y1 <= y0:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            env = np.exp(-(r / R) ** 2 * 2.2).astype(np.float32)
            # THIN rings at full contrast; the envelope only gates visibility
            # (first cut multiplied cos by env BEFORE thresholding -> blobs)
            ln = _sstep(0.80, 0.94, (0.5 + 0.5 * np.cos(2 * np.pi * r / pitch + ph))
                        .astype(np.float32)) * _sstep(0.10, 0.30, env)
            sub = rings[y0:y1, x0:x1]
            np.maximum(sub, ln, out=sub)
            better = env > env_best[y0:y1, x0:x1]
            hsub = huef[y0:y1, x0:x1]
            hsub[better] = (hb + (r[better] / pitch) * 0.085) % 1.0
            env_best[y0:y1, x0:x1] = np.maximum(env_best[y0:y1, x0:x1], env)
        return rings.astype(np.float32), env_best, huef

    def spec(F, s, h, w):
        lines, env, huef = F
        lane = np.clip(lines * (0.55 + 0.45 * env) * 1.15, 0, 1)
        return _soul_spec_v2(lane, m_tex=6 * (env - 0.5))

    def paint(F, src_lum):
        lines, env, huef = F
        base = np.float32((0.030, 0.060, 0.085))
        art = np.empty(lines.shape + (3,), np.float32)
        art[:] = base[None, None, :]
        glow = _hsv_field(huef, 0.82, 0.060 + 0.180 * lines)
        m = np.clip(lines * (0.35 + 0.65 * env) * 1.3, 0, 1)[..., None]
        art = art * (1 - m) + glow * m
        return np.clip(art, 0, 1), np.full(lines.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_star_chart")  # grave-sky cartography: razor star pins, hairline
# constellation chords, three faint nebula hue washes under crushed indigo.
def _b_starchart():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 17)
        stars = _sstep(0.915, 0.975, _noise(h, w, s, (1.7, 3.2)))
        n_anchor = int(380 * sr * sr) + 80
        pts = np.stack([rng.uniform(0, w, n_anchor),
                        rng.uniform(0, h, n_anchor)], -1).astype(np.float32)
        from scipy.spatial import cKDTree
        tree = cKDTree(pts)
        _, idx = tree.query(pts, k=3, workers=-1)
        canvas = np.zeros((h, w), np.uint8)
        big = np.zeros((h, w), np.uint8)
        for i in range(n_anchor):
            for j in idx[i, 1:]:
                if i < j:
                    cv2.line(canvas, (int(pts[i, 0]), int(pts[i, 1])),
                             (int(pts[j, 0]), int(pts[j, 1])), 255, 1)
            cv2.circle(big, (int(pts[i, 0]), int(pts[i, 1])),
                       max(1, int(1.4 * sr)), 255, -1)
        chords = (canvas > 0).astype(np.float32)
        anchors = (big > 0).astype(np.float32)
        neb1 = _noise(h, w, s ^ 0xF1, (140, 320))
        neb2 = _noise(h, w, s ^ 0xF2, (120, 300))
        return stars.astype(np.float32), chords, anchors, \
            neb1.astype(np.float32), neb2.astype(np.float32)

    def spec(F, s, h, w):
        stars, chords, anchors, neb1, neb2 = F
        lane = np.clip(0.8 * chords + np.clip(_gauss(anchors, 1.5) * 1.6, 0, 1), 0, 1)
        return _soul_spec_v2(lane, pins=np.clip(stars + anchors, 0, 1),
                             m_tex=5 * (neb1 - 0.5))

    def paint(F, src_lum):
        stars, chords, anchors, neb1, neb2 = F
        art = np.empty(stars.shape + (3,), np.float32)
        art[:] = np.float32((0.050, 0.040, 0.130))[None, None, :]
        art[..., 1] += 0.09 * neb1 - 0.035
        art[..., 0] += 0.10 * neb2 - 0.04
        bone = np.float32((0.62, 0.65, 0.78))
        m = np.clip(stars * 0.75 + anchors * 0.65 + chords * 0.30, 0, 1)[..., None]
        art = art * (1 - m) + bone[None, None, :] * m * 0.60
        return np.clip(art, 0, 1), np.full(stars.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_serpent_scale")  # imbricated scale rows — fine crescent rims, keeled
# centers, alternating crushed emerald/abyss rows that flash row-by-row.
def _b_serpentscale():
    def fields(h, w, s):
        sr = _sr(h, w)
        yy, xx = _coords(h, w)
        rng = _rng(s, 19)
        a = float(rng.uniform(0, np.pi))
        p = max(7.0, 10.5 * sr)
        wx = (_noise(h, w, s ^ 0x101, (40, 110)) - 0.5) * (6.0 * sr)
        wy = (_noise(h, w, s ^ 0x102, (44, 116)) - 0.5) * (6.0 * sr)
        u = (xx * np.cos(a) + yy * np.sin(a) + wx) / p
        v = (-xx * np.sin(a) + yy * np.cos(a) + wy) / (p * 1.15)
        row = np.floor(v)
        u2 = u + 0.5 * (row % 2.0)
        fu = (u2 - np.floor(u2) - 0.5).astype(np.float32)
        fv = (v - row - 0.62).astype(np.float32)
        d = np.sqrt(fu * fu + (fv * 1.25) ** 2).astype(np.float32)
        rim = ((1.0 - _sstep(0.045, 0.10, np.abs(d - 0.50))) *
               (fv < 0.05)).astype(np.float32)
        keel = ((1.0 - _sstep(0.04, 0.10, np.abs(fu))) *
                _sstep(-0.42, -0.05, fv) * (fv < 0.0)).astype(np.float32)
        parity = (row % 2.0).astype(np.float32)
        shash = _frac(np.floor(u2) * 0.61803 + row * 0.75487).astype(np.float32)
        return rim, keel, parity, shash

    def spec(F, s, h, w):
        rim, keel, parity, shash = F
        lane = np.clip(0.95 * rim + 0.45 * keel, 0, 1)
        return _soul_spec_v2(lane, m_tex=8 * (shash - 0.5))

    def paint(F, src_lum):
        rim, keel, parity, shash = F
        emerald = np.float32((0.030, 0.140, 0.075))
        abyss = np.float32((0.055, 0.050, 0.170))
        art = emerald[None, None, :] * (1 - parity)[..., None] + \
            abyss[None, None, :] * parity[..., None]
        art *= (0.65 + 0.5 * shash)[..., None]
        art = np.clip(art + 0.10 * rim[..., None] + 0.04 * keel[..., None], 0, 1)
        return art, np.full(rim.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_nova_burst")  # scattered micro star-detonations, each with its own
# crushed hue halo — a six-color nova field on near-black violet.
def _b_novaburst():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 23)
        rays = np.zeros((h, w), np.uint8)
        hueidx = np.zeros((h, w), np.uint8)
        n = int(560 * sr * sr) + 90
        for i in range(n):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            L = rng.uniform(9, 26) * sr
            k = int(rng.integers(0, 6))
            cv2.circle(hueidx, (int(cx), int(cy)), max(2, int(L * 0.60)), k + 1, -1)
            nr = int(rng.integers(6, 12))
            a0 = rng.uniform(0, 2 * np.pi)
            for j in range(nr):
                a = a0 + j * (2 * np.pi / nr) + rng.uniform(-0.2, 0.2)
                Lj = L * rng.uniform(0.55, 1.0)
                cv2.line(rays, (int(cx), int(cy)),
                         (int(cx + np.cos(a) * Lj), int(cy + np.sin(a) * Lj)), 255, 1)
        raysf = (rays > 0).astype(np.float32)
        glow = np.clip(_gauss(raysf, 1.6 * sr) * 2.0, 0, 1)
        return raysf, glow.astype(np.float32), hueidx

    def spec(F, s, h, w):
        raysf, glow, hueidx = F
        return _soul_spec_v2(glow, pins=raysf, m_tex=5 * (glow - 0.5))

    def paint(F, src_lum):
        raysf, glow, hueidx = F
        base = np.float32((0.060, 0.040, 0.105))
        hues = [0.96, 0.08, 0.13, 0.46, 0.60, 0.78]
        # hueidx partitions the canvas (a pixel carries at most one nova hue;
        # 0 = no nova). The old 6-pass sequential blend left art==base wherever
        # m==0, so the net result is a SINGLE base->matching-hue blend by the
        # per-pixel glow amount. Gather the matching color from a 7-entry LUT
        # (slot 0 = base, slots 1..6 = the nova hues) and blend once.
        # Bit-identical to the loop (verified array_equal, maxd 0.0), ~4.5x faster.
        pal = np.empty((7, 3), np.float32)
        pal[0] = base
        for k, hh in enumerate(hues):
            pal[k + 1] = _hsv_field(hh, 0.85, 0.24)
        col = pal[hueidx]
        m = (np.clip(glow * 1.3 + raysf * 0.4, 0, 1) *
             (hueidx > 0).astype(np.float32))[..., None]
        art = base[None, None, :] * (1 - m) + col * m
        return np.clip(art, 0, 1), np.full(raysf.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_circuit_soul")  # haunted circuitry: hairline traces walking a
# seed-rotated grid, via-dots pinned razor; copper vs teal trace families.
def _b_circuitsoul():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 29)
        a = float(rng.uniform(0, np.pi))
        dirs = [np.float32((np.cos(a), np.sin(a))),
                np.float32((-np.sin(a), np.cos(a)))]
        lines = np.zeros((h, w), np.uint8)
        fam = np.zeros((h, w), np.uint8)
        vias = np.zeros((h, w), np.uint8)
        n = int(680 * sr * sr) + 110
        for i in range(n):
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            f = int(rng.integers(0, 2))
            d = int(rng.integers(0, 2))
            segs = int(rng.integers(4, 9))
            pts = [(x, y)]
            for _ in range(segs):
                step = rng.uniform(9, 30) * sr
                sign = 1.0 if rng.uniform(0, 1) < 0.5 else -1.0
                vec = dirs[d] * step * sign
                x, y = x + float(vec[0]), y + float(vec[1])
                pts.append((x, y))
                d = 1 - d
            for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
                cv2.line(lines, (int(x0), int(y0)), (int(x1), int(y1)), 255, 1)
                cv2.line(fam, (int(x0), int(y0)), (int(x1), int(y1)), f + 1, 1)
            for (px, py) in pts[1:-1]:
                cv2.circle(vias, (int(px), int(py)), max(1, int(1.3 * sr)), 255, -1)
        lf = (lines > 0).astype(np.float32)
        vf = (vias > 0).astype(np.float32)
        halo = np.clip(_gauss(lf, 1.3 * sr) * 1.8, 0, 1)
        return lf, vf, halo.astype(np.float32), fam

    def spec(F, s, h, w):
        lf, vf, halo, fam = F
        return _soul_spec_v2(np.clip(halo * 0.9 + lf * 0.4, 0, 1),
                             pins=vf, m_tex=6 * (halo - 0.5))

    def paint(F, src_lum):
        lf, vf, halo, fam = F
        art = np.empty(lf.shape + (3,), np.float32)
        art[:] = np.float32((0.032, 0.048, 0.040))[None, None, :]
        copper = np.float32((0.265, 0.130, 0.050))
        teal = np.float32((0.040, 0.155, 0.165))
        m1 = (np.clip((fam == 1).astype(np.float32) + 0, 0, 1) *
              np.clip(lf + halo * 0.5, 0, 1))[..., None]
        m2 = ((fam == 2).astype(np.float32) * np.clip(lf + halo * 0.5, 0, 1))[..., None]
        art = art * (1 - m1) + copper[None, None, :] * m1
        art = art * (1 - m2) + teal[None, None, :] * m2
        art = np.clip(art + 0.10 * vf[..., None], 0, 1)
        return art, np.full(lf.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_geode_vein")  # agate banding: warped contour bands, a five-hue
# crushed sequence cycling band-by-band, druzy pin pockets every few bands.
def _b_geodevein():
    def fields(h, w, s):
        sr = _sr(h, w)
        f = _noise(h, w, s, (40, 90, 180))
        f = _gauss(f, 2.0 * sr)
        t = _n01(f) * 26.0
        band = np.floor(t)
        ft = (t - band).astype(np.float32)
        bl = (1.0 - _sstep(0.05, 0.13, np.minimum(ft, 1 - ft))).astype(np.float32)
        bidx = (band % 5.0).astype(np.float32)
        bhash = _frac(band * 0.61803).astype(np.float32)
        druzy = (_sstep(0.86, 0.95, _noise(h, w, s ^ 0x111, (2.0, 4.0))) *
                 (bhash > 0.72)).astype(np.float32)
        return bl, bidx, bhash, druzy

    def spec(F, s, h, w):
        bl, bidx, bhash, druzy = F
        lane = np.clip(0.95 * bl + 0.30 * _sstep(0.5, 0.8, bhash), 0, 1)
        return _soul_spec_v2(lane, pins=druzy, m_tex=8 * (bhash - 0.5))

    def paint(F, src_lum):
        bl, bidx, bhash, druzy = F
        hues = np.float32([0.78, 0.50, 0.11, 0.93, 0.58])   # violet teal gold rose ice
        hue = hues[bidx.astype(np.int32)]
        val = 0.055 + 0.115 * bhash
        art = _hsv_field(hue, 0.80, val)
        art = np.clip(art * (1.0 - 0.45 * bl)[..., None] + 0.12 * druzy[..., None], 0, 1)
        return art, np.full(bl.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_moire_phantom")  # CIRCULAR moire — two families of fine concentric
# rings from scattered centers; their interference draws wandering hyperbolic
# phantom curves (omnidirectional — the linear version collapsed to stripes).
def _b_moirephantom():
    def fields(h, w, s):
        sr = _sr(h, w)
        yy, xx = _coords(h, w)
        rng = _rng(s, 31)
        p = max(3.4, 5.0 * sr)
        wv = (_noise(h, w, s ^ 0x121, (60, 150)) - 0.5) * (5.0 * sr)

        def ringfam(seed_off, pitch):
            acc = np.zeros((h, w), np.float32)
            r2 = _rng(s, seed_off)
            for _ in range(3):
                cx, cy = r2.uniform(-0.2 * w, 1.2 * w), r2.uniform(-0.2 * h, 1.2 * h)
                r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) + wv
                acc = np.maximum(acc, _sstep(0.74, 0.93,
                                  (0.5 + 0.5 * np.cos(2 * np.pi * r / pitch))
                                  .astype(np.float32)))
            return acc

        l1 = ringfam(41, p)
        l2 = ringfam(43, p * 1.022)
        beat = _n01(_gauss(l1 * l2, 7.0 * sr))
        return l1.astype(np.float32), l2.astype(np.float32), beat.astype(np.float32)

    def spec(F, s, h, w):
        l1, l2, beat = F
        lane = np.clip((l1 + l2) * (0.22 + 0.78 * beat) * 0.75, 0, 1)
        return _soul_spec_v2(lane, m_tex=9 * (beat - 0.5))

    def paint(F, src_lum):
        l1, l2, beat = F
        steel = np.float32((0.040, 0.115, 0.140))
        rose = np.float32((0.190, 0.050, 0.110))
        art = steel[None, None, :] * (1 - beat)[..., None] + \
            rose[None, None, :] * beat[..., None]
        art *= (0.50 + 0.50 * np.clip(l1 + l2, 0, 1))[..., None]
        return np.clip(art, 0, 1), np.full(beat.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


@_def("fs_aurora_threads")  # curtain filaments: micro threads gated into
# curtains, hue sweeping green->teal->violet across the sweep axis — many
# colors live in the paint at once.
def _b_aurorathreads():
    def fields(h, w, s):
        sr = _sr(h, w)
        yy, xx = _coords(h, w)
        rng = _rng(s, 37)
        a = float(rng.uniform(0, np.pi))
        p = max(3.4, 5.4 * sr)
        wu = (_noise(h, w, s ^ 0x131, (26, 70)) - 0.5) * (16.0 * sr)
        u = (xx * np.cos(a) + yy * np.sin(a) + wu) / p
        threads = ((0.5 + 0.5 * np.cos(2 * np.pi * u)) ** 3.0).astype(np.float32)
        # crisp curtain RIBBONS with hard edges (soft gate read as blotch);
        # edge bands get their own highlight lane
        gf = _noise(h, w, s ^ 0x132, (34, 95))
        gate = _sstep(0.47, 0.55, gf)
        edge = (_sstep(0.42, 0.50, gf) - _sstep(0.52, 0.60, gf)).astype(np.float32)
        sweep = _n01(_noise(h, w, s ^ 0x133, (120, 300)))
        return threads, gate.astype(np.float32), np.clip(edge, 0, 1), \
            sweep.astype(np.float32)

    def spec(F, s, h, w):
        threads, gate, edge, sweep = F
        lane = np.clip(threads * (0.20 + 0.80 * gate) * 1.25 + 0.55 * edge, 0, 1)
        return _soul_spec_v2(lane, m_tex=6 * (gate - 0.5))

    def paint(F, src_lum):
        threads, gate, edge, sweep = F
        hue = 0.30 + 0.50 * sweep                      # green -> teal -> violet
        val = 0.045 + 0.205 * threads * (0.22 + 0.78 * gate) + 0.05 * edge
        art = _hsv_field(hue, 0.86, val)
        return art, np.full(threads.shape, 0.92, np.float32)

    return {"fields": fields, "spec": spec, "paint": paint}


# ════════════════════════════════════════════════ WIRING
def _fs_mk(fid):
    d = SOULS[fid]

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        F = _fs_fields(fid, _WORKS, _WORKS, _seed_int(seed))
        M, G, B = d["spec"](F, _seed_int(seed), _WORKS, _WORKS)
        M, G, B = [cv2.resize(np.clip(np.asarray(a, np.float32), 0, 255), (fw, fh),
                              interpolation=cv2.INTER_LINEAR) for a in (M, G, B)]
        out = np.zeros((fh, fw, 4), np.uint8)
        mm = np.clip(m2, 0, 1)
        inv = 1.0 - mm
        out[:, :, 0] = np.clip(M * mm + 4.0 * inv, 0, 255)
        out[:, :, 1] = np.clip(np.clip(G, 14, 255) * mm + 120.0 * inv, 0, 255)
        out[:, :, 2] = np.clip(np.clip(B, 16, 255) * mm + 16.0 * inv, 0, 255)
        out[:, :, 3] = 255
        return out

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        F = _fs_fields(fid, _WORKS, _WORKS, _seed_int(seed))
        art_w, k_w = d["paint"](F, None)
        art = cv2.resize(np.clip(art_w, 0, 1), (fw, fh), interpolation=cv2.INTER_LINEAR)
        k = cv2.resize(np.clip(k_w, 0, 1), (fw, fh), interpolation=cv2.INTER_LINEAR)
        strength = np.clip(m2 * float(pm), 0, 1)
        kk = (k * strength)[..., None]
        # SOULS ship PRE-CRUSHED: the art replaces the source directly (no
        # lum-scaling) so drag-and-drop = instant working color shift
        out = np.clip(src * (1.0 - kk) + art * kk, 0, 1)
        return out.astype(np.float32)

    return spec_fn, paint_fn


def install_into_engine(mono_reg):
    n = 0
    try:
        import engine.expansions.fusions as _fus
        for fid in SOULS:
            entry = _fs_mk(fid)
            mono_reg[fid] = entry
            _fus.FUSION_REGISTRY[fid] = entry
            n += 1
    except Exception:
        for fid in SOULS:
            mono_reg[fid] = _fs_mk(fid)
            n += 1
    return f"fractured-souls: {n} drag-and-drop color-shift finishes live (5 cores + {n - 5} textured)"
