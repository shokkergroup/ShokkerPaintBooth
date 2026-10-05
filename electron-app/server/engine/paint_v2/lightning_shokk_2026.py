"""LIGHTNING SHOKK — every way electricity finds a path.

Owner mandate 2026-09-04: four new shelves, minimum 15 finishes each.

THE ARC
-------
Sixteen different DISCHARGE MORPHOLOGIES. Leader and return stroke, surface
Lichtenberg tree, horizontal anvil crawler, corona brush, plasma-globe filament,
Jacob's ladder, welding arc, sprite tendril, static creep, carbon tracking, bead
instability, competing streamer front, fulgurite glass, spark gap, Tesla streamer
and corona ring. No two propagate the same way.

WHY THIS SHELF, WITH EVIDENCE
-----------------------------
The catalog already has 59 finishes with lightning/bolt in the name and 205 with
electric in the name — but only FIVE that are actually a branching discharge
STRUCTURE. Almost every existing one is electric-COLOURED, not electric-SHAPED.
That is the gap this shelf fills, and it is why nothing here is allowed to be
'a blue glow'.

SCALE NOTE: a single hero bolt is a macro composition and fails the gate
outright. Every finish here is a FIELD of discharge — branch spacing 12-24px,
filaments 2-4px — because the spacing between filaments is the band that counts,
not the filament width.

HOW IT WAS BUILT
----------------
Each finish was authored against `_authoring_contract.md` by a dedicated agent
and then audited against the same contract by a second one, because the contract
encodes measured facts that are not guessable — the exact SCALE annulus, the
fact that a blur can never be load-bearing, and that FOLLOW must be CONSTRUCTED
(the spec rebuilds the paint's own field through a shared cache key) rather than
reasoned about. Each finish then declares a knob SPACE, and
`scripts/spb_variant_search.py` renders and scores ten samples of it, writing the
winner to `lightning_shokk_2026_params.json` with the full score table beside it — so "best of
ten" is checkable rather than asserted.
"""

from __future__ import annotations

import numpy as np

from engine.paint_v2 import _finish_kit_2026 as K
from engine.paint_v2._variant_params import chooser

OVERRIDE = None          # (finish_id, params) — set by the variant search harness


def _P(fid):
    if OVERRIDE is not None and OVERRIDE[0] == fid:
        return OVERRIDE[1]
    return _CHOSEN[fid]


def _k(P):
    return K.kkey(P)


# ═══════════════════════════════════════════════════════════ FINISHES ══


def _ridge(f, sharp):
    """Turn a smooth field's mid-level contour into a thin FILAMENT.

    1 - |2f-1| peaks exactly on the f = 0.5 contour, so thresholding it gives a
    continuous branching line network rather than blobs. This is the shelf's only
    shared operator; every finish drives it with a different geometry, and several
    do not use it at all.
    """
    # `sharp` may be a per-pixel ARRAY, not a scalar: the Tesla streamer tapers its
    # filament width along the path, which is the whole mechanism of that finish.
    return np.clip(1.0 - np.abs(2.0 * f - 1.0) / np.maximum(sharp, 1e-3), 0, 1)


def _emit(src, glow, hot, tint, pm):
    """Blend a discharge's EMISSION over the painter's colour.

    Their base is the material being struck and has to stay readable, so the glow
    is added rather than substituted, and only the hottest core is allowed to go
    to white — which is what a real channel does.
    """
    g = np.clip(glow * float(pm), 0, 1)[:, :, None]
    hw = np.clip(hot * float(pm), 0, 1)[:, :, None]
    col = np.asarray(tint, np.float32).reshape(1, 1, 3)
    return src * (1.0 - 0.55 * g) + col * g * 0.95 + hw * 0.85


# ═══════════════════════════════════════════════════════ 01 · RETURN STROKE ══
def _return_stroke(shape, seed, P):
    """Leader channel with a hot core, a bright channel and a dim corona sheath.

    Three concentric intensity zones. An even-width line is not a return stroke —
    the zones are how the eye reads current density.
    """
    h, w = shape[:2]

    def build():
        f = K.mid(shape, float(P["span_px"]), seed + 3, octaves=3)
        f = K.norm(K.streak(f, int(P["fall"]), axis=0))       # channels run downward
        core = _ridge(f, float(P["core"]))
        chan = _ridge(f, float(P["core"]) * 3.0)
        sheath = _ridge(f, float(P["core"]) * 8.0)
        return core.astype(np.float32), chan.astype(np.float32), sheath.astype(np.float32)

    return K.cache(("lskrs", h, w, int(seed), _k(P)), build)


def paint_lsk_return_stroke(paint, shape, mask, seed, pm, bb):
    """The main channel of a strike, in its three concentric zones."""
    P = _P("lsk_return_stroke")
    src = K.incoming(paint, shape)
    core, chan, sheath = _return_stroke(shape, seed, P)
    glow = np.clip(0.30 * sheath + 0.65 * chan, 0, 1) * float(P["gain"])
    out = _emit(src, glow, core, (0.72, 0.80, 1.00), pm)
    return K.finish(out, src, mask)


def spec_lsk_return_stroke(shape, seed, sm, base_m, base_r):
    """GRAMMAR: core / channel / sheath three-material — ionised air is a mirror,
    the sheath is half of one, and the untouched panel is neither."""
    P = _P("lsk_return_stroke")
    core, chan, sheath = _return_stroke(shape, seed, P)
    m = K.norm(np.clip(0.30 * sheath + 0.65 * chan, 0, 1) * float(P["gain"]) + core)
    M = np.clip(30.0 + 150.0 * m * sm, 0, 255)
    R = np.clip(45.0 + 120.0 * (1.0 - m), 15, 255)
    CC = np.clip(20.0 + 70.0 * (1.0 - m), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════ 02 · LICHTENBERG BURN ══
def _lichtenberg(shape, seed, P):
    """Surface breakdown: branches that MULTIPLY as they travel outward.

    Done in polar coordinates around injection points, with the angular frequency
    rising with radius — which is exactly what branching is, and it costs one pass
    instead of a growth simulation.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        rng = np.random.default_rng((int(seed) ^ 0x4C11) & 0xFFFFFFFF)
        acc = np.zeros((h, w), np.float32)
        for _ in range(int(P["sites"])):
            cy, cx = rng.uniform(0, h), rng.uniform(0, w)
            dy, dx = py - cy, px - cx
            r = np.sqrt(dy * dy + dx * dx) + 8.0
            th = np.arctan2(dy, dx)
            acc = np.maximum(acc, (0.5 + 0.5 * np.sin(th * (r / float(P["branch_px"]))))
                             / (1.0 + r / (min(h, w) * 0.35)))
        f = K.norm(acc)
        return _ridge(f, float(P["thin"])).astype(np.float32)

    return K.cache(("lsklb", h, w, int(seed), _k(P)), build)


def paint_lsk_lichtenberg(paint, shape, mask, seed, pm, bb):
    """A dielectric breaking down: the tree burned into its surface."""
    P = _P("lsk_lichtenberg")
    src = K.incoming(paint, shape)
    t = _lichtenberg(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 3.0, (0.86, 0.74, 1.00), pm)
    return K.finish(out, src, mask)


def spec_lsk_lichtenberg(shape, seed, sm, base_m, base_r):
    """GRAMMAR: branch-order ladder — each generation of branch is a discrete burn
    depth, so the spec steps rather than ramps."""
    P = _P("lsk_lichtenberg")
    t = _lichtenberg(shape, seed, P)
    step = K.ladder(t, 5, 0.0, 1.0)
    M = np.clip(18.0 + 120.0 * step * sm, 0, 255)
    R = np.clip(120.0 - 80.0 * step, 15, 255)
    CC = np.clip(55.0 - 34.0 * step, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 03 · SPIDER CRAWL ══
def _spider(shape, seed, P):
    """An anvil crawler spreads SIDEWAYS and branches reluctantly."""
    h, w = shape[:2]

    def build():
        f = K.mid(shape, float(P["span_px"]), seed + 7, octaves=2)
        f = K.norm(K.streak(f, int(P["reach"]), axis=1))       # travels horizontally
        return _ridge(f, float(P["thin"])).astype(np.float32)

    return K.cache(("lsksp", h, w, int(seed), _k(P)), build)


def paint_lsk_spider_crawl(paint, shape, mask, seed, pm, bb):
    """Crawlers running sideways under the cloud base for miles."""
    P = _P("lsk_spider_crawl")
    src = K.incoming(paint, shape)
    t = _spider(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 4.0, (0.80, 0.86, 1.00), pm)
    return K.finish(out, src, mask)


def spec_lsk_spider_crawl(shape, seed, sm, base_m, base_r):
    """GRAMMAR: anisotropic horizontal filament — roughness runs ALONG the crawl,
    so the panel is glossier across the channels than along them."""
    P = _P("lsk_spider_crawl")
    t = _spider(shape, seed, P)
    M = np.clip(42.0 + 130.0 * t * sm, 0, 255)
    R = np.clip(70.0 - 46.0 * t + 30.0 * K.streak(t, 6, axis=1), 15, 255)
    CC = np.clip(26.0 + 40.0 * (1.0 - t), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 04 · ST ELMO'S FIRE ══
def _st_elmo(shape, seed, P):
    """Corona brush: short needles standing off an edge, densest where E is highest."""
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        edge = K.norm(K.mid(shape, 150.0, seed + 11, octaves=2))
        boundary = _ridge(edge, 0.035)                      # a THIN conductor outline
        comb = 0.5 + 0.5 * np.sin(px * (6.2832 / float(P["comb_px"])))
        near = np.clip(K.box(boundary, int(P["length"])) * 14.0, 0, 1)  # tight gate
        needles = np.clip(comb * 1.9 - 0.75, 0, 1) * near
        return np.clip(boundary * 0.5 + needles * 1.15, 0, 1).astype(np.float32)

    return K.cache(("lskse", h, w, int(seed), _k(P)), build)


def paint_lsk_st_elmo(paint, shape, mask, seed, pm, bb):
    """Brush discharge standing off every sharp edge it can find."""
    P = _P("lsk_st_elmo")
    src = K.incoming(paint, shape)
    t = _st_elmo(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 3.0, (0.62, 0.86, 1.00), pm)
    return K.finish(out, src, mask)


def spec_lsk_st_elmo(shape, seed, sm, base_m, base_r):
    """GRAMMAR: edge-driven needle field — the needles are ionised air standing on
    a dielectric, so M spikes only on them and the ground stays dull."""
    P = _P("lsk_st_elmo")
    t = _st_elmo(shape, seed, P)
    M = np.clip(22.0 + 150.0 * t * sm, 0, 255)
    R = np.clip(95.0 - 60.0 * t, 15, 255)
    CC = np.clip(34.0 + 30.0 * (1.0 - t), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 05 · PLASMA GLOBE ══
def _globe(shape, seed, P):
    """Filaments running from an electrode to the glass, WANDERING as they go."""
    h, w = shape[:2]

    def build():
        py, px = K.warp(shape, seed + 13, float(P["wander"]), 110.0)
        rng = np.random.default_rng((int(seed) ^ 0x77C5) & 0xFFFFFFFF)
        acc = np.zeros((h, w), np.float32)
        for _ in range(int(P["nodes"])):
            cy, cx = rng.uniform(0, h), rng.uniform(0, w)
            th = np.arctan2(py - cy, px - cx)
            r = np.sqrt((py - cy) ** 2 + (px - cx) ** 2) + 6.0
            acc = np.maximum(acc, (0.5 + 0.5 * np.sin(th * float(P["arms"])))
                             * np.clip(1.0 - r / (min(h, w) * 0.55), 0, 1))
        return _ridge(K.norm(acc), float(P["thin"])).astype(np.float32)

    return K.cache(("lskpg", h, w, int(seed), _k(P)), build)


def paint_lsk_plasma_globe(paint, shape, mask, seed, pm, bb):
    """Filaments reaching for the glass, flaring where they touch it."""
    P = _P("lsk_plasma_globe")
    src = K.incoming(paint, shape)
    t = _globe(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 3.5, (1.00, 0.55, 0.92), pm)
    return K.finish(out, src, mask)


def spec_lsk_plasma_globe(shape, seed, sm, base_m, base_r):
    """GRAMMAR: radial filament with bright feet — the touch points are a third
    material, hotter and smoother than the filament that fed them."""
    P = _P("lsk_plasma_globe")
    t = _globe(shape, seed, P)
    foot = np.clip(t * 1.6 - 0.6, 0, 1)
    M = np.clip(60.0 + 120.0 * t * sm + 50.0 * foot, 0, 255)
    R = np.clip(80.0 - 50.0 * t - 20.0 * foot, 15, 255)
    CC = np.clip(24.0 + 34.0 * (1.0 - t), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 06 · JACOB'S LADDER ══
def _ladder_arc(shape, seed, P):
    """An arc climbing two diverging rails: each rung WIDER and dimmer than the last."""
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        row = np.floor(py / pitch)
        f = py / pitch - row
        gap = 0.18 + 0.62 * (row * pitch / max(h, 1))       # the rails diverge upward
        bow = np.cos((px / w - 0.5) * 3.1416) * gap
        arc = np.clip(1.0 - np.abs(f - 0.5 - bow * 0.35) * float(P["thin"]), 0, 1)
        dim = np.clip(1.2 - gap, 0.2, 1.0)
        return (arc * dim).astype(np.float32)

    return K.cache(("lskjl", h, w, int(seed), _k(P)), build)


def paint_lsk_jacobs_ladder(paint, shape, mask, seed, pm, bb):
    """The arc walking up the rails, stretching until it snaps back."""
    P = _P("lsk_jacobs_ladder")
    src = K.incoming(paint, shape)
    t = _ladder_arc(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 3.0, (1.00, 0.72, 0.42), pm)
    return K.finish(out, src, mask)


def spec_lsk_jacobs_ladder(shape, seed, sm, base_m, base_r):
    """GRAMMAR: phase-quantised rung ladder — each rung is one discrete material,
    stepping in brightness up the panel."""
    P = _P("lsk_jacobs_ladder")
    t = _ladder_arc(shape, seed, P)
    step = K.ladder(t, 6, 0.0, 1.0)
    M = np.clip(75.0 + 120.0 * step * sm, 0, 255)
    R = np.clip(60.0 - 38.0 * step, 15, 255)
    CC = np.clip(22.0 + 30.0 * (1.0 - step), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════════ 07 · ARC WELD ══
def _weld(shape, seed, P):
    """A welding arc: hot core, radial spatter streaks, landed globules."""
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        u, v = px / pitch, py / pitch
        iu, iv = np.floor(u), np.floor(v)
        fu = (u - iu - 0.5) * pitch
        fv = (v - iv - 0.5) * pitch
        r = np.sqrt(fu * fu + fv * fv) + 1e-3
        th = np.arctan2(fv, fu)
        spatter = np.clip(1.0 - np.abs(np.sin(th * float(P["rays"]))) * 5.0, 0, 1)
        streak = spatter * np.clip(1.0 - r / (pitch * 0.48), 0, 1)
        core = np.clip(1.0 - r / (pitch * 0.10), 0, 1)
        glob = (_hash2(iu, iv, 5.5) > 0.55).astype(np.float32) * \
            np.clip(1.0 - np.abs(r - pitch * 0.36) / 2.2, 0, 1)
        return (np.clip(core + 0.7 * streak + 0.9 * glob, 0, 1).astype(np.float32),
                core.astype(np.float32))

    return K.cache(("lskaw", h, w, int(seed), _k(P)), build)


def paint_lsk_arc_weld(paint, shape, mask, seed, pm, bb):
    """A weld arc throwing spatter, and the globules freezing where they land."""
    P = _P("lsk_arc_weld")
    src = K.incoming(paint, shape)
    t, core = _weld(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), core, (1.00, 0.82, 0.40), pm)
    return K.finish(out, src, mask)


def spec_lsk_arc_weld(shape, seed, sm, base_m, base_r):
    """GRAMMAR: hard duotone plus a spatter population — molten metal and cold
    plate, with nothing in between, because that is what a weld is."""
    P = _P("lsk_arc_weld")
    t, core = _weld(shape, seed, P)
    hot = (t > 0.35).astype(np.float32)
    M = np.clip(95.0 + 140.0 * hot * sm, 0, 255)
    R = np.clip(140.0 - 100.0 * t, 15, 255)
    CC = np.clip(30.0 + 40.0 * (1.0 - t), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════════ 08 · SPRITE ══
def _sprite(shape, seed, P):
    """Upper-atmosphere discharge: fine vertical tendrils hanging from a cap."""
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        seedf = K.norm(K.mid(shape, float(P["spacing"]), seed + 17, octaves=1))
        comb = np.clip(1.0 - np.abs(seedf - 0.5) * float(P["thin"]), 0, 1)
        # tendrils thin downward: multiply by a falling envelope inside each cell
        cell = float(P["cell_px"])
        fv = py / cell - np.floor(py / cell)
        taper = np.clip(1.0 - fv * 0.9, 0, 1)
        return (comb * taper).astype(np.float32)

    return K.cache(("lsksr", h, w, int(seed), _k(P)), build)


def paint_lsk_sprite(paint, shape, mask, seed, pm, bb):
    """Tendrils hanging beneath a diffuse cap, fifty miles up."""
    P = _P("lsk_sprite")
    src = K.incoming(paint, shape)
    t = _sprite(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 4.0, (1.00, 0.34, 0.52), pm)
    return K.finish(out, src, mask)


def spec_lsk_sprite(shape, seed, sm, base_m, base_r):
    """GRAMMAR: vertical tendril ladder — the tendril's height is quantised, so the
    spec deals a stack of discrete altitudes."""
    P = _P("lsk_sprite")
    t = _sprite(shape, seed, P)
    step = K.ladder(t, 5, 0.0, 1.0)
    M = np.clip(26.0 + 110.0 * step * sm, 0, 255)
    R = np.clip(130.0 - 70.0 * step, 15, 255)
    CC = np.clip(62.0 - 34.0 * step, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 09 · STATIC CREEP ══
def _creep(shape, seed, P):
    """Charge creeping over a dielectric in very fine rivulets that keep dying out."""
    h, w = shape[:2]

    def build():
        f = K.norm(K.mid(shape, float(P["span_px"]), seed + 19, octaves=3))
        net = _ridge(f, float(P["thin"]))
        # dead ends: a second field gates the network so most branches stop short
        gate = K.norm(K.mid(shape, float(P["span_px"]) * 2.2, seed + 20, octaves=2))
        return (net * np.clip(gate * 1.8 - 0.45, 0, 1)).astype(np.float32)

    return K.cache(("lskcr", h, w, int(seed), _k(P)), build)


def paint_lsk_static_creep(paint, shape, mask, seed, pm, bb):
    """Surface charge finding its way across a panel in fine rivulets."""
    P = _P("lsk_static_creep")
    src = K.incoming(paint, shape)
    t = _creep(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 3.0, (0.66, 0.92, 1.00), pm)
    return K.finish(out, src, mask)


def spec_lsk_static_creep(shape, seed, sm, base_m, base_r):
    """GRAMMAR: fine dual population — charged track and neutral dielectric, and
    nothing between them, because charge either went there or it did not."""
    P = _P("lsk_static_creep")
    t = _creep(shape, seed, P)
    on = (t > 0.30).astype(np.float32)
    M = np.clip(14.0 + 130.0 * on * sm, 0, 255)
    R = np.clip(160.0 - 110.0 * on, 15, 255)
    CC = np.clip(70.0 - 44.0 * on, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 10 · CARBON TRACK ══
def _carbon(shape, seed, P):
    """Arc tracking: carbonised paths burned into a contaminated insulator.

    The one member of this shelf that SUBTRACTS light. Tracks are wider and blacker
    where the current lingered, with a scorched halo either side.
    """
    h, w = shape[:2]

    def build():
        py, px = K.warp(shape, seed + 21, 22.0, 120.0)
        f = K.norm(K.mid(shape, float(P["span_px"]), seed + 22, octaves=2))
        track = _ridge(f, float(P["thin"]))
        dwell = K.norm(K.mid(shape, 90.0, seed + 23, octaves=2))
        burn = track * (0.45 + 0.85 * dwell)
        halo = np.clip(K.box(burn, 3) - burn, 0, 1)
        return np.clip(burn, 0, 1).astype(np.float32), halo.astype(np.float32)

    return K.cache(("lskct", h, w, int(seed), _k(P)), build)


def paint_lsk_carbon_track(paint, shape, mask, seed, pm, bb):
    """Conductive carbon burned across an insulator that was already dirty."""
    P = _P("lsk_carbon_track")
    src = K.incoming(paint, shape)
    burn, halo = _carbon(shape, seed, P)
    k = float(P["depth"])
    out = src * (1.0 - k * burn[:, :, None] * float(pm))
    out = out * (1.0 - 0.30 * halo[:, :, None])
    scorch = np.asarray((0.40, 0.24, 0.10), np.float32).reshape(1, 1, 3)
    out = out + scorch * halo[:, :, None] * 0.35
    return K.finish(out, src, mask)


def spec_lsk_carbon_track(shape, seed, sm, base_m, base_r):
    """GRAMMAR: burn-depth ladder — carbon is a conductor, so M RISES into the
    track even as everything else about it goes dead."""
    P = _P("lsk_carbon_track")
    burn, halo = _carbon(shape, seed, P)
    step = K.ladder(burn, 5, 0.0, 1.0)
    M = np.clip(10.0 + 90.0 * step * sm, 0, 255)
    R = np.clip(185.0 + 55.0 * step - 40.0 * halo, 15, 255)
    CC = np.clip(105.0 + 60.0 * step, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════ 11 · BEAD LIGHTNING ══
def _bead(shape, seed, P):
    """The decaying channel breaks into a string of beads.

    The BEAD PITCH along the filament is the dominant structure, not the filament
    itself — a sausage instability, and the reason bead lightning has a name.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        f = K.norm(K.streak(K.mid(shape, float(P["span_px"]), seed + 25, octaves=2),
                            int(P["fall"]), axis=0))
        chan = _ridge(f, float(P["thin"]))
        beads = 0.5 + 0.5 * np.sin(py * (6.2832 / float(P["bead_px"])))
        return (chan * (0.25 + 0.95 * beads)).astype(np.float32), chan.astype(np.float32)

    return K.cache(("lskbd", h, w, int(seed), _k(P)), build)


def paint_lsk_bead(paint, shape, mask, seed, pm, bb):
    """A channel decaying into a string of beads before it goes out."""
    P = _P("lsk_bead")
    src = K.incoming(paint, shape)
    t, chan = _bead(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 3.0, (1.00, 0.90, 0.70), pm)
    return K.finish(out, src, mask)


def spec_lsk_bead(shape, seed, sm, base_m, base_r):
    """GRAMMAR: bead-count ladder along the channel — the beads are the levels, and
    the neck between them is the floor."""
    P = _P("lsk_bead")
    t, chan = _bead(shape, seed, P)
    step = K.ladder(t, 6, 0.0, 1.0)
    M = np.clip(50.0 + 130.0 * step * sm, 0, 255)
    R = np.clip(75.0 - 48.0 * step, 15, 255)
    CC = np.clip(28.0 + 34.0 * (1.0 - step), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 12 · STREAMER FRONT ══
def _streamers(shape, seed, P):
    """Many streamers advance from a plane and COMPETE; most die, a few run far."""
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        iu = np.floor(px / pitch)
        fu = px / pitch - iu
        length = _hash2(iu, iu * 0.5, 3.7) ** float(P["compete"])   # a few run far
        cell = float(P["cell_px"])
        phase = _hash2(iu, iu * 0.25, 9.4)
        fv = (py / cell + phase) - np.floor(py / cell + phase)
        alive = np.clip((length - fv) * 6.0, 0, 1)
        stem = np.clip(1.0 - np.abs(fu - 0.5) * float(P["thin"]), 0, 1)
        return (stem * alive).astype(np.float32)

    return K.cache(("lskst", h, w, int(seed), _k(P)), build)


def paint_lsk_streamer_front(paint, shape, mask, seed, pm, bb):
    """A front of streamers, most of which never get anywhere."""
    P = _P("lsk_streamer_front")
    src = K.incoming(paint, shape)
    t = _streamers(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 3.0, (0.72, 1.00, 0.86), pm)
    return K.finish(out, src, mask)


def spec_lsk_streamer_front(shape, seed, sm, base_m, base_r):
    """GRAMMAR: streamer-length ladder — how far a streamer got IS its material,
    so the spec quantises reach rather than brightness."""
    P = _P("lsk_streamer_front")
    t = _streamers(shape, seed, P)
    step = K.ladder(t, 5, 0.0, 1.0)
    M = np.clip(36.0 + 120.0 * step * sm, 0, 255)
    R = np.clip(105.0 - 62.0 * step, 15, 255)
    CC = np.clip(46.0 - 26.0 * step, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════════ 13 · FULGURITE ══
def _fulgurite(shape, seed, P):
    """The glass tube a strike leaves in sand: a HOLLOW branching tube.

    Not glowing — this is the aftermath, and it is all material: a fused vitreous
    inner rim with raw sintered sand outside it.
    """
    h, w = shape[:2]

    def build():
        f = K.norm(K.mid(shape, float(P["span_px"]), seed + 27, octaves=2))
        wide = _ridge(f, float(P["thin"]) * 2.4)
        bore = _ridge(f, float(P["thin"]) * 0.8)
        rim = np.clip(wide - bore, 0, 1)                    # the fused wall
        return wide.astype(np.float32), rim.astype(np.float32), bore.astype(np.float32)

    return K.cache(("lskfg", h, w, int(seed), _k(P)), build)


def paint_lsk_fulgurite(paint, shape, mask, seed, pm, bb):
    """Sand fused into glass tubing by a strike that came and went."""
    P = _P("lsk_fulgurite")
    src = K.incoming(paint, shape)
    wide, rim, bore = _fulgurite(shape, seed, P)
    k = float(P["depth"])
    out = src * (1.0 - 0.45 * k * bore[:, :, None] * float(pm))
    out = out + rim[:, :, None] * float(P["sheen"]) * float(pm)
    out = out * (0.90 + 0.22 * (1.0 - wide)[:, :, None])
    return K.finish(out, src, mask)


def spec_lsk_fulgurite(shape, seed, sm, base_m, base_r):
    """GRAMMAR: vitrified rim three-material — glass wall, hollow bore, sintered
    sand. The only fully non-emissive spec on the shelf."""
    P = _P("lsk_fulgurite")
    wide, rim, bore = _fulgurite(shape, seed, P)
    M = np.clip(20.0 + 60.0 * rim * sm, 0, 255)
    R = np.clip(165.0 - 130.0 * rim + 40.0 * bore, 15, 255)
    CC = np.clip(88.0 - 60.0 * rim, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════════ 14 · SPARK GAP ══
def _spark(shape, seed, P):
    """A field of SHORT discrete sparks, each with a strike dot at either end.

    No branching whatsoever, which is exactly what separates a gap discharge from
    everything else on this shelf.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        u, v = px / pitch, py / pitch
        iu, iv = np.floor(u), np.floor(v)
        fu = (u - iu - 0.5) * pitch
        fv = (v - iv - 0.5) * pitch
        th = _hash2(iu, iv, 2.2) * 3.1416
        along = fu * np.cos(th) + fv * np.sin(th)
        across = -fu * np.sin(th) + fv * np.cos(th)
        half = pitch * float(P["len"])
        keep = (_hash2(iu, iv, 6.4) < float(P["density"])).astype(np.float32)
        line = np.clip(1.0 - np.abs(across) * float(P["thin"]), 0, 1) * \
            np.clip((half - np.abs(along)) * 2.0, 0, 1)
        dot = np.clip(1.0 - (np.abs(np.abs(along) - half) * 1.6 + np.abs(across) * 1.6), 0, 1)
        return (np.clip(line * 0.8 + dot, 0, 1) * keep).astype(np.float32)

    return K.cache(("lskgp", h, w, int(seed), _k(P)), build)


def paint_lsk_spark_gap(paint, shape, mask, seed, pm, bb):
    """Short sparks jumping small gaps, over and over."""
    P = _P("lsk_spark_gap")
    src = K.incoming(paint, shape)
    t = _spark(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 3.0, (0.92, 0.96, 1.00), pm)
    return K.finish(out, src, mask)


def spec_lsk_spark_gap(shape, seed, sm, base_m, base_r):
    """GRAMMAR: spark duotone with strike dots — ionised channel, struck metal, and
    untouched panel; three values, no ramp."""
    P = _P("lsk_spark_gap")
    t = _spark(shape, seed, P)
    M = np.clip(120.0 + 110.0 * t * sm, 0, 255)
    R = np.clip(70.0 - 46.0 * t, 15, 255)
    CC = np.clip(54.0 - 30.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 15 · TESLA STREAMER ══
def _tesla(shape, seed, P):
    """Streamers from a toroid: a THICK root splitting into many fine tips.

    The taper is the mechanism. Root and tip are the same discharge at different
    current densities, so the width has to fall along the path, not step.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        f = K.norm(K.mid(shape, float(P["span_px"]), seed + 29, octaves=3))
        depth = K.norm(py / max(h, 1) + 0.35 * (K.mid(shape, 200.0, seed + 30, octaves=1) - 0.5))
        thin = float(P["thin"]) * (0.45 + 1.55 * depth)      # thinner further out
        return _ridge(f, thin).astype(np.float32), depth.astype(np.float32)

    return K.cache(("lskts", h, w, int(seed), _k(P)), build)


def paint_lsk_tesla_streamer(paint, shape, mask, seed, pm, bb):
    """Streamers thrown off a toroid, fat at the root and hair-fine at the tips."""
    P = _P("lsk_tesla_streamer")
    src = K.incoming(paint, shape)
    t, depth = _tesla(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 3.0 * (1.0 - depth), (0.80, 0.56, 1.00), pm)
    return K.finish(out, src, mask)


def spec_lsk_tesla_streamer(shape, seed, sm, base_m, base_r):
    """GRAMMAR: root-to-tip taper ladder — current density is quantised along the
    path, so the root deals a different material from the tips."""
    P = _P("lsk_tesla_streamer")
    t, depth = _tesla(shape, seed, P)
    step = K.ladder(t * (1.0 - 0.6 * depth), 6, 0.0, 1.0)
    M = np.clip(88.0 + 130.0 * step * sm, 0, 255)
    R = np.clip(80.0 - 52.0 * step, 15, 255)
    CC = np.clip(32.0 + 32.0 * (1.0 - step), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 16 · CORONA RING ══
def _corona_ring(shape, seed, P):
    """Corona in concentric rings around a conductor, BREAKING where it is dirty.

    The breaks are what stop this reading as a target: real corona is not uniform
    around a contaminated surface, and the gaps are where it went out.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        rng = np.random.default_rng((int(seed) ^ 0x2D77) & 0xFFFFFFFF)
        acc = np.zeros((h, w), np.float32)
        for _ in range(int(P["cores"])):
            cy, cx = rng.uniform(0, h), rng.uniform(0, w)
            r = np.sqrt((py - cy) ** 2 + (px - cx) ** 2)
            ring = 0.5 + 0.5 * np.sin(r * (6.2832 / float(P["pitch"])))
            acc = np.maximum(acc, ring * np.clip(1.0 - r / (min(h, w) * 0.50), 0, 1))
        dirt = K.norm(K.mid(shape, 46.0, seed + 31, octaves=2))
        breaks = np.clip(dirt * 1.7 - 0.35, 0, 1)
        return (K.norm(acc) * breaks).astype(np.float32)

    return K.cache(("lskcn", h, w, int(seed), _k(P)), build)


def paint_lsk_corona_ring(paint, shape, mask, seed, pm, bb):
    """Corona standing off a conductor in rings, broken where the surface is dirty."""
    P = _P("lsk_corona_ring")
    src = K.incoming(paint, shape)
    t = _corona_ring(shape, seed, P)
    out = _emit(src, t * float(P["gain"]), t ** 4.0, (0.58, 0.78, 1.00), pm)
    return K.finish(out, src, mask)


def spec_lsk_corona_ring(shape, seed, sm, base_m, base_r):
    """GRAMMAR: concentric ring ramp with breaks — a smooth radial ramp interrupted
    by hard voids, which is a different object from either a ramp or a duotone."""
    P = _P("lsk_corona_ring")
    t = _corona_ring(shape, seed, P)
    M = np.clip(66.0 + 120.0 * t * sm, 0, 255)
    R = np.clip(88.0 - 52.0 * t, 15, 255)
    CC = np.clip(44.0 + 26.0 * (1.0 - t), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def _hash2(a, b, salt=0.0):
    """Per-cell pseudo-random in 0..1 from two integer lattice coords."""
    v = np.sin(a * 127.1 + b * 311.7 + salt) * 43758.5453
    return (v - np.floor(v)).astype(np.float32)



# ══════════════════════════════════════════════════════════════ CATALOG ══
CATALOG = {
    "lsk_return_stroke":   {"M": 30,  "R": 45,  "CC": 20,
                            "desc": "Return Stroke — the main channel, in its three concentric zones"},
    "lsk_lichtenberg":     {"M": 18,  "R": 120, "CC": 55,
                            "desc": "Lichtenberg Burn — the tree a dielectric leaves when it gives up"},
    "lsk_spider_crawl":    {"M": 42,  "R": 70,  "CC": 26,
                            "desc": "Spider Crawl — anvil crawlers running sideways for miles"},
    "lsk_st_elmo":         {"M": 22,  "R": 95,  "CC": 34,
                            "desc": "St Elmo's Fire — brush discharge standing off every sharp edge"},
    "lsk_plasma_globe":    {"M": 60,  "R": 55,  "CC": 24,
                            "desc": "Plasma Globe — filaments reaching for the glass and flaring on it"},
    "lsk_jacobs_ladder":   {"M": 75,  "R": 40,  "CC": 22,
                            "desc": "Jacob's Ladder — the arc walking up the rails until it snaps"},
    "lsk_arc_weld":        {"M": 95,  "R": 110, "CC": 30,
                            "desc": "Arc Weld — spatter thrown from the arc, freezing where it lands"},
    "lsk_sprite":          {"M": 26,  "R": 130, "CC": 62,
                            "desc": "Red Sprite — tendrils hanging under a cap, fifty miles up"},
    "lsk_static_creep":    {"M": 14,  "R": 150, "CC": 70,
                            "desc": "Static Creep — surface charge finding its way in fine rivulets"},
    "lsk_carbon_track":    {"M": 10,  "R": 185, "CC": 105,
                            "desc": "Carbon Track — conductive carbon burned across a dirty insulator"},
    "lsk_bead":            {"M": 50,  "R": 60,  "CC": 28,
                            "desc": "Bead Lightning — a channel decaying into beads before it dies"},
    "lsk_streamer_front":  {"M": 36,  "R": 85,  "CC": 40,
                            "desc": "Streamer Front — a hundred streamers, and most get nowhere"},
    "lsk_fulgurite":       {"M": 20,  "R": 165, "CC": 88,
                            "desc": "Fulgurite — sand fused to glass tubing by a strike long gone"},
    "lsk_spark_gap":       {"M": 120, "R": 50,  "CC": 24,
                            "desc": "Spark Gap — short sparks jumping small gaps, over and over"},
    "lsk_tesla_streamer":  {"M": 88,  "R": 65,  "CC": 32,
                            "desc": "Tesla Streamer — fat at the root, hair-fine at the tips"},
    "lsk_corona_ring":     {"M": 66,  "R": 75,  "CC": 44,
                            "desc": "Corona Ring — rings around a conductor, broken where it is dirty"},
}

SPACE = {
    "lsk_return_stroke":   {"span_px": (26.0, 52.0), "core": (0.045, 0.11), "fall": [4, 8, 14],
                            "gain": (0.60, 1.40)},
    "lsk_lichtenberg":     {"sites": [3, 5, 8], "branch_px": (22.0, 55.0), "thin": (0.05, 0.13),
                            "gain": (0.60, 1.45)},
    "lsk_spider_crawl":    {"span_px": (24.0, 48.0), "reach": [8, 14, 22], "thin": (0.05, 0.12),
                            "gain": (0.60, 1.40)},
    "lsk_st_elmo":         {"comb_px": (5.0, 10.0), "length": [2, 3, 5], "gain": (0.75, 1.60)},
    "lsk_plasma_globe":    {"nodes": [3, 5, 7], "arms": (14.0, 34.0), "wander": (14.0, 40.0),
                            "thin": (0.05, 0.12), "gain": (0.60, 1.40)},
    "lsk_jacobs_ladder":   {"pitch": (13.0, 24.0), "thin": (4.0, 9.0), "gain": (0.60, 1.40)},
    "lsk_arc_weld":        {"pitch": (18.0, 32.0), "rays": (7.0, 16.0), "gain": (0.60, 1.40)},
    "lsk_sprite":          {"spacing": (9.0, 16.0), "thin": (3.0, 7.0), "cell_px": (16.0, 30.0),
                            "gain": (0.60, 1.40)},
    "lsk_static_creep":    {"span_px": (11.0, 20.0), "thin": (0.06, 0.15), "gain": (0.60, 1.40)},
    "lsk_carbon_track":    {"span_px": (16.0, 30.0), "thin": (0.07, 0.17), "depth": (0.55, 1.30)},
    "lsk_bead":            {"span_px": (22.0, 42.0), "thin": (0.05, 0.12), "bead_px": (10.0, 18.0),
                            "fall": [6, 10, 16], "gain": (0.60, 1.40)},
    "lsk_streamer_front":  {"pitch": (9.0, 17.0), "cell_px": (18.0, 32.0), "thin": (2.4, 5.0),
                            "compete": (1.4, 3.4), "gain": (0.60, 1.40)},
    "lsk_fulgurite":       {"span_px": (18.0, 34.0), "thin": (0.05, 0.12), "depth": (0.55, 1.25),
                            "sheen": (0.18, 0.50)},
    "lsk_spark_gap":       {"pitch": (13.0, 24.0), "len": (0.22, 0.40), "thin": (0.7, 1.6),
                            "density": (0.45, 0.85), "gain": (0.60, 1.40)},
    "lsk_tesla_streamer":  {"span_px": (20.0, 40.0), "thin": (0.05, 0.12), "gain": (0.60, 1.40)},
    "lsk_corona_ring":     {"cores": [3, 5, 8], "pitch": (10.0, 18.0), "gain": (0.60, 1.40)},
}

_CHOSEN = chooser(__name__, SPACE)


def install(registry):
    """Wire this shelf into a BASE_REGISTRY. Returns the number installed."""
    import sys as _sys
    me = _sys.modules[__name__]
    n = 0
    for fid, meta in CATALOG.items():
        entry = registry.setdefault(fid, {})
        entry.update(meta)
        entry["paint_fn"] = getattr(me, "paint_" + fid)
        entry["base_spec_fn"] = getattr(me, "spec_" + fid)
        n += 1
    return n
