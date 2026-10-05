"""SLITHERIN — sixteen snakes, sixteen different skins.

Owner mandate 2026-09-04: four new shelves, minimum 15 finishes each.

THE ARC
-------
SCALE ARCHITECTURE, not snake-coloured patterns. Keeled versus smooth,
overlapping cycloid versus non-overlapping granular, wide ventral scutes versus
tiny dorsal beads, anisotropically stretched hood scales — the way the scales
TILE is built differently in every finish, and the pattern rides on top of that
geometry rather than standing in for it.

WHY THIS SHELF, WITH EVIDENCE
-----------------------------
This shelf has the most competition in the catalog of any built today: 84
snake-named finishes and 30 reptile-scale ones already exist, including
fc_snakeskin, fm_python_skin, fm_diamondback, alligator_hide and crocodile. A
generic scaly pattern would fail the uniqueness gate against them outright.
What earns these their place is that the scale FIELD itself differs in each.

COLOUR: the painter's base colour is the snake's ground colour, and every
pattern tone is derived from it, so a red car gives a red snake.

HOW IT WAS BUILT
----------------
Each finish was authored against `_authoring_contract.md` by a dedicated agent
and then audited against the same contract by a second one, because the contract
encodes measured facts that are not guessable — the exact SCALE annulus, the
fact that a blur can never be load-bearing, and that FOLLOW must be CONSTRUCTED
(the spec rebuilds the paint's own field through a shared cache key) rather than
reasoned about. Each finish then declares a knob SPACE, and
`scripts/spb_variant_search.py` renders and scores ten samples of it, writing the
winner to `slitherin_2026_params.json` with the full score table beside it — so "best of
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


def _hash2(a, b, salt=0.0):
    v = np.sin(a * 127.1 + b * 311.7 + salt) * 43758.5453
    return (v - np.floor(v)).astype(np.float32)


def _brick(shape, px_w, px_h, seed, stagger=0.5):
    """Offset-row lattice — the tiling every overlapping-scale snake is built on.

    Returns (fu, fv, iu, iv) in cell-local coordinates. Each finish then puts its
    OWN profile on this lattice: a keel ridge, a rounded overlap shadow, a stretched
    lozenge, a hollow imprint. The tiling is shared infrastructure; the scale is not.
    """
    h, w = shape[:2]
    py, px = K.px(shape)
    v = py / float(px_h)
    iv = np.floor(v)
    off = (iv % 2.0) * float(stagger)
    u = px / float(px_w) + off
    iu = np.floor(u)
    return (u - iu - 0.5).astype(np.float32), (v - iv - 0.5).astype(np.float32), iu, iv


def _tone(src, t, dark, light):
    """Derive the pattern's tones FROM the painter's colour, so a red car gives a
    red snake. Never impose a palette."""
    d = src * float(dark)
    l = np.clip(src * float(light) + 0.06, 0, 1)
    a = t[:, :, None]
    return d * (1.0 - a) + l * a


# ═══════════════════════════════════════════════════ 01 · RETICULATED PYTHON ══
def _reticulated(shape, seed, P):
    """The NET is the subject: a pale mesh around dark irregular polygons.

    Worley cell WALLS give the net; the fine scale texture inside each polygon is
    kept deliberately low-contrast so the net stays the dominant band.
    """
    h, w = shape[:2]

    def build():
        val, edge, ang = K.cells(shape, seed + 3, float(P["cell_px"]), jitter=0.9)
        net = np.clip(1.0 - edge * float(P["net"]), 0, 1)
        fu, fv, iu, iv = _brick(shape, float(P["scale_px"]), float(P["scale_px"]) * 0.8, seed)
        fine = np.clip(1.0 - (fu * fu + fv * fv) * 6.0, 0, 1)
        return np.clip(net * 0.86 + 0.14 * fine, 0, 1).astype(np.float32)

    return K.cache(("sltrt", h, w, int(seed), _k(P)), build)


def paint_slt_reticulated(paint, shape, mask, seed, pm, bb):
    """The reticulated python's net: pale mesh, dark blocks, fine scales inside."""
    P = _P("slt_reticulated")
    src = K.incoming(paint, shape)
    t = _reticulated(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.42, 1.55)
    return K.finish(out, src, mask)


def spec_slt_reticulated(shape, seed, sm, base_m, base_r):
    """GRAMMAR: net outline duotone — the interstitial skin between scales is a
    different material from the scales themselves, and the net is that skin."""
    P = _P("slt_reticulated")
    t = _reticulated(shape, seed, P)
    M = np.clip(25.0 + 70.0 * t * sm, 0, 255)
    R = np.clip(150.0 - 80.0 * t, 15, 255)
    CC = np.clip(80.0 - 44.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 02 · KEELED VIPER ══
def _keeled(shape, seed, P):
    """Every scale carries a raised central RIDGE running head to tail.

    The keel is why a viper looks matte and directional while a smooth snake looks
    wet: it breaks the specular into a line instead of a highlight.
    """
    h, w = shape[:2]

    def build():
        fu, fv, iu, iv = _brick(shape, float(P["scale_px"]), float(P["scale_px"]) * 0.72, seed + 5)
        body = np.clip(1.0 - (fu * fu * 1.5 + fv * fv * 3.0) * 3.2, 0, 1)
        keel = np.clip(1.0 - np.abs(fu) * float(P["keel"]), 0, 1) * body
        flank = body - keel * 0.6
        return np.clip(0.30 + 0.85 * keel + 0.25 * flank, 0, 1).astype(np.float32)

    return K.cache(("sltkv", h, w, int(seed), _k(P)), build)


def paint_slt_keeled_viper(paint, shape, mask, seed, pm, bb):
    """Keeled scales: a raised ridge down every one of them."""
    P = _P("slt_keeled_viper")
    src = K.incoming(paint, shape)
    t = _keeled(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.48, 1.42)
    return K.finish(out, src, mask)


def spec_slt_keeled_viper(shape, seed, sm, base_m, base_r):
    """GRAMMAR: keel anisotropic relief — roughness falls only along the keel line,
    so the shine is a stripe on every scale rather than a spot."""
    P = _P("slt_keeled_viper")
    t = _keeled(shape, seed, P)
    M = np.clip(40.0 + 80.0 * t * sm, 0, 255)
    R = np.clip(175.0 - 95.0 * t, 15, 255)
    CC = np.clip(70.0 - 34.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════ 03 · SEA SNAKE GLOSS ══
def _cycloid(shape, seed, P):
    """Smooth cycloid scales, no keel, heavily overlapping like roof tiles.

    The ONLY structure is the overlap shadow at each scale's trailing edge — which
    is what a wet-adapted snake looks like, and the opposite of the keeled viper.
    """
    h, w = shape[:2]

    def build():
        fu, fv, iu, iv = _brick(shape, float(P["scale_px"]), float(P["scale_px"]) * 0.55, seed + 7)
        d = np.sqrt(fu * fu * 1.1 + fv * fv * 3.4)
        body = np.clip(1.0 - d * 1.9, 0, 1)
        lip = np.clip((d - 0.42) * float(P["lip"]), 0, 1) * (fv > 0)
        return np.clip(0.42 + 0.75 * body - 0.55 * lip, 0, 1).astype(np.float32)

    return K.cache(("sltcy", h, w, int(seed), _k(P)), build)


def paint_slt_cycloid_gloss(paint, shape, mask, seed, pm, bb):
    """Smooth overlapping scales, wet-looking and free of any keel."""
    P = _P("slt_cycloid_gloss")
    src = K.incoming(paint, shape)
    t = _cycloid(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.50, 1.50)
    return K.finish(out, src, mask)


def spec_slt_cycloid_gloss(shape, seed, sm, base_m, base_r):
    """GRAMMAR: smooth overlap ramp — one material, very glossy, its roughness
    following the tile's curve. The glossiest spec on the shelf."""
    P = _P("slt_cycloid_gloss")
    t = _cycloid(shape, seed, P)
    M = np.clip(30.0 + 60.0 * t * sm, 0, 255)
    R = np.clip(62.0 - 42.0 * t, 15, 255)
    CC = np.clip(30.0 - 12.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 04 · VENTRAL SCUTE ══
def _scute(shape, seed, P):
    """The belly: single-file transverse plates, much larger than dorsal scales.

    Strictly one-dimensional geometry, which is what makes it unmistakable against
    every other member of this shelf.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        wob = (K.mid(shape, 260.0, seed + 9, octaves=2) - 0.5) * pitch * 0.35
        v = (py + wob) / pitch
        f = v - np.floor(v)
        cup = np.clip(1.0 - np.abs(f - 0.45) * 2.4, 0, 1)
        edge = np.clip(1.0 - np.abs(f - 0.96) * float(P["edge"]), 0, 1)
        return np.clip(0.30 + 0.80 * cup - 0.45 * edge, 0, 1).astype(np.float32)

    return K.cache(("sltvs", h, w, int(seed), _k(P)), build)


def paint_slt_ventral_scute(paint, shape, mask, seed, pm, bb):
    """Belly scutes: wide transverse plates with a soft cup to each one."""
    P = _P("slt_ventral_scute")
    src = K.incoming(paint, shape)
    t = _scute(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.52, 1.46)
    return K.finish(out, src, mask)


def spec_slt_ventral_scute(shape, seed, sm, base_m, base_r):
    """GRAMMAR: transverse plate ladder — each plate is one flat material and the
    joint between plates is another."""
    P = _P("slt_ventral_scute")
    t = _scute(shape, seed, P)
    M = np.clip(K.ladder(t, 5, 18.0, 70.0) * sm, 0, 255)
    R = np.clip(K.ladder(1.0 - t, 5, 40.0, 130.0), 15, 255)
    CC = np.clip(K.ladder(1.0 - t, 4, 30.0, 78.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════ 05 · BOA SADDLE ══
def _saddle(shape, seed, P):
    """Dark saddles with a pinched waist, joined along the spine, over fine scales."""
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        v = py / pitch
        iv = np.floor(v)
        fv = v - iv - 0.5
        iu = np.floor(px / float(P["waist_px"]))
        wid = 0.22 + 0.46 * _hash2(iu, iv, 5.1)          # each saddle its own waist
        fu = px / float(P["waist_px"]) - iu - 0.5
        body = np.clip(1.0 - np.abs(fu) * 2.2, 0, 1)
        sad = np.clip(1.0 - np.abs(fv) / np.maximum(wid, 0.05), 0, 1) * body
        fu2, fv2, _, _ = _brick(shape, float(P["scale_px"]), float(P["scale_px"]) * 0.8, seed + 11)
        fine = np.clip(1.0 - (fu2 * fu2 + fv2 * fv2) * 5.0, 0, 1)
        return np.clip(0.82 - 0.72 * sad + 0.14 * fine, 0, 1).astype(np.float32)

    return K.cache(("sltbs", h, w, int(seed), _k(P)), build)


def paint_slt_boa_saddle(paint, shape, mask, seed, pm, bb):
    """Boa saddles: dark blotches pinched at the waist, riding a fine scale field."""
    P = _P("slt_boa_saddle")
    src = K.incoming(paint, shape)
    t = _saddle(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.34, 1.48)
    return K.finish(out, src, mask)


def spec_slt_boa_saddle(shape, seed, sm, base_m, base_r):
    """GRAMMAR: saddle domain palette — the saddle and the ground are different
    pigment loads, so they scatter differently as well as reading darker."""
    P = _P("slt_boa_saddle")
    t = _saddle(shape, seed, P)
    M = np.clip(22.0 + 62.0 * t * sm, 0, 255)
    R = np.clip(160.0 - 78.0 * t, 15, 255)
    CC = np.clip(88.0 - 44.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════ 06 · SIDEWINDER MICRO ══
def _sidewinder(shape, seed, P):
    """Very fine granular desert scales: NON-overlapping beads, each its own dome."""
    h, w = shape[:2]

    def build():
        fu, fv, iu, iv = _brick(shape, float(P["bead_px"]), float(P["bead_px"]) * 0.9,
                                seed + 13, stagger=0.5)
        d = np.sqrt(fu * fu + fv * fv)
        bead = np.clip(1.0 - d * float(P["round"]), 0, 1) ** 1.4
        sand = _hash2(iu, iv, 4.4) * 0.30
        return np.clip(0.34 + 0.70 * bead + sand * bead, 0, 1).astype(np.float32)

    return K.cache(("sltsw", h, w, int(seed), _k(P)), build)


def paint_slt_sidewinder_micro(paint, shape, mask, seed, pm, bb):
    """Desert granules: the finest skin on the shelf, matched to sand."""
    P = _P("slt_sidewinder_micro")
    src = K.incoming(paint, shape)
    t = _sidewinder(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.58, 1.34)
    return K.finish(out, src, mask)


def spec_slt_sidewinder_micro(shape, seed, sm, base_m, base_r):
    """GRAMMAR: fine dual population — bead and interstice, with per-bead variation
    so no two granules deal quite the same value."""
    P = _P("slt_sidewinder_micro")
    t = _sidewinder(shape, seed, P)
    M = np.clip(35.0 + 55.0 * t * sm, 0, 255)
    R = np.clip(200.0 - 80.0 * t, 15, 255)
    CC = np.clip(95.0 - 40.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════ 07 · GABOON GEOMETRIC ══
def _gaboon(shape, seed, P):
    """Hard-edged hourglasses and triangles: the most graphic snake alive.

    The only member of this shelf whose pattern is ANGULAR rather than organic, so
    every boundary is a straight line and every corner is sharp.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        u = px / pitch
        v = py / pitch
        iu, iv = np.floor(u), np.floor(v)
        fu, fv = u - iu - 0.5, v - iv - 0.5
        tri = np.abs(fu) + np.abs(fv)                  # L1 metric: diamonds, not circles
        band = (np.floor(iv * 0.5) % 2.0)                 # motif alternates by BAND
        hour = np.clip((float(P["size"]) - tri) * float(P["hard"]), 0, 1)
        alt = np.clip((tri - float(P["size"]) * 0.55) * float(P["hard"]), 0, 1)
        return np.clip(np.where(band > 0.5, hour, alt), 0, 1).astype(np.float32)

    return K.cache(("sltgb", h, w, int(seed), _k(P)), build)


def paint_slt_gaboon_geometric(paint, shape, mask, seed, pm, bb):
    """Gaboon geometry: hourglasses and triangles with razor boundaries."""
    P = _P("slt_gaboon_geometric")
    src = K.incoming(paint, shape)
    t = _gaboon(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.38, 1.58)
    return K.finish(out, src, mask)


def spec_slt_gaboon_geometric(shape, seed, sm, base_m, base_r):
    """GRAMMAR: angular facet palette — flat values inside hard straight boundaries,
    with no gradient anywhere on the panel."""
    P = _P("slt_gaboon_geometric")
    t = _gaboon(shape, seed, P)
    M = np.clip(28.0 + 74.0 * t * sm, 0, 255)
    R = np.clip(185.0 - 96.0 * t, 15, 255)
    CC = np.clip(94.0 - 50.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════ 08 · MILK SNAKE BAND ══
def _milk(shape, seed, P):
    """Crisp transverse TRICOLOUR bands in a strict repeating order.

    The order and the hard edges are the identity — a milk snake is a sequence, not
    a texture, and getting the sequence right is what makes it read.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        wob = (K.mid(shape, 300.0, seed + 15, octaves=2) - 0.5) * float(P["band_px"]) * 0.5
        v = (py + wob) / (float(P["band_px"]) * 3.0)
        f = (v - np.floor(v)) * 3.0
        band = np.floor(f)                              # 0, 1, 2 in strict order
        return (band / 2.0).astype(np.float32)

    return K.cache(("sltmb", h, w, int(seed), _k(P)), build)


def paint_slt_milk_band(paint, shape, mask, seed, pm, bb):
    """Tricolour banding in the order that makes a milk snake a milk snake."""
    P = _P("slt_milk_band")
    src = K.incoming(paint, shape)
    t = _milk(shape, seed, P)
    a = float(P["gain"])
    lum = src.mean(axis=2, keepdims=True)
    pale = np.clip(src * 0.55 + lum * 0.30 + 0.32, 0, 1)      # the cream band
    out = np.where(t[:, :, None] < 0.25, src * 0.28,
                   np.where(t[:, :, None] < 0.75, np.clip(src * (1.0 + a), 0, 1), pale))
    return K.finish(out.astype(np.float32), src, mask)


def spec_slt_milk_band(shape, seed, sm, base_m, base_r):
    """GRAMMAR: band triplet ladder — three bands, three materials, exactly."""
    P = _P("slt_milk_band")
    t = _milk(shape, seed, P)
    M = np.clip(K.ladder(t, 3, 20.0, 92.0) * sm, 0, 255)
    R = np.clip(K.ladder(1.0 - t, 3, 46.0, 150.0), 15, 255)
    CC = np.clip(K.ladder(t, 3, 36.0, 96.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════ 09 · CORN SNAKE BLOTCH ══
def _corn(shape, seed, P):
    """Rounded dorsal blotches with a thin continuous OUTLINE, plus lateral spots.

    That unbroken dark ring is the diagnostic: without it the same blotches read as
    a boa, and with it they read as a corn snake.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        u, v = px / pitch, py / pitch
        iu, iv = np.floor(u), np.floor(v)
        jx = _hash2(iu, iv, 2.4) - 0.5
        fu = (u - iu - 0.5 - jx * 0.35)
        fv = (v - iv - 0.5)
        d = np.sqrt(fu * fu * 0.8 + fv * fv * 1.6)
        fill = np.clip((float(P["size"]) - d) * 5.0, 0, 1)
        ring = np.clip(1.0 - np.abs(d - float(P["size"])) * float(P["ring"]), 0, 1)
        return np.clip(0.68 + 0.32 * fill - 0.85 * ring, 0, 1).astype(np.float32)

    return K.cache(("sltcb", h, w, int(seed), _k(P)), build)


def paint_slt_corn_blotch(paint, shape, mask, seed, pm, bb):
    """Corn snake blotches, each ringed in a thin unbroken outline."""
    P = _P("slt_corn_blotch")
    src = K.incoming(paint, shape)
    t = _corn(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.30, 1.52)
    return K.finish(out, src, mask)


def spec_slt_corn_blotch(shape, seed, sm, base_m, base_r):
    """GRAMMAR: blotch outline duotone — the outline is melanin-dense and matte,
    which is a genuinely different material from the blotch it encloses."""
    P = _P("slt_corn_blotch")
    t = _corn(shape, seed, P)
    M = np.clip(26.0 + 66.0 * t * sm, 0, 255)
    R = np.clip(170.0 - 82.0 * t, 15, 255)
    CC = np.clip(86.0 - 42.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════ 10 · SUNBEAM IRIDESCENCE ══
def _sunbeam(shape, seed, P):
    """Nanoridges on smooth scales split light; each scale sits at its own angle.

    So the interference ORDER is per-scale, not per-pixel — which is why a real
    sunbeam snake shimmers in patches rather than as a smooth rainbow.
    """
    h, w = shape[:2]

    def build():
        fu, fv, iu, iv = _brick(shape, float(P["scale_px"]), float(P["scale_px"]) * 0.62, seed + 17)
        d = np.sqrt(fu * fu + fv * fv * 2.6)
        body = np.clip(1.0 - d * 2.0, 0, 1)
        order = _hash2(iu, iv, 7.1)
        return body.astype(np.float32), order.astype(np.float32)

    return K.cache(("sltsi", h, w, int(seed), _k(P)), build)


def paint_slt_sunbeam_iris(paint, shape, mask, seed, pm, bb):
    """Iridescence that lives on the SCALE, so it shimmers in patches."""
    P = _P("slt_sunbeam_iris")
    src = K.incoming(paint, shape)
    body, order = _sunbeam(shape, seed, P)
    phase = (order - 0.5) * float(P["spread"])
    shifted = K.hue_rotate(src, phase)
    a = np.clip(body * float(P["gain"]), 0, 1)[:, :, None]
    out = src * (1.0 - a) + np.clip(shifted * 1.35, 0, 1) * a
    out = out * (0.62 + 0.55 * body[:, :, None])
    return K.finish(out.astype(np.float32), src, mask)


def spec_slt_sunbeam_iris(shape, seed, sm, base_m, base_r):
    """GRAMMAR: per-scale interference two-state — each scale is either in a bright
    order or a dark one, which is what makes the shimmer patchy rather than smooth."""
    P = _P("slt_sunbeam_iris")
    body, order = _sunbeam(shape, seed, P)
    # `order` is a per-scale CONSTANT with its own geometry; leaning on it pulled the
    # spec's detail away from the paint's and scored 0.154 on FOLLOW. The scale body
    # is what the paint's structure actually is, so all three channels read that and
    # the interference state is reduced to a small tint on top.
    st = (order > 0.5).astype(np.float32)
    M = np.clip(150.0 + 90.0 * body * sm - 10.0 * st, 0, 255)
    R = np.clip(28.0 + 46.0 * (1.0 - body) + 5.0 * st, 15, 255)
    CC = np.clip(16.0 + 26.0 * (1.0 - body), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 11 · SHED SKIN ══
def _shed(shape, seed, P):
    """The papery shed: scale IMPRINTS as hollow outlines, not solid scales."""
    h, w = shape[:2]

    def build():
        fu, fv, iu, iv = _brick(shape, float(P["scale_px"]), float(P["scale_px"]) * 0.7, seed + 19)
        d = np.sqrt(fu * fu + fv * fv * 2.2)
        outline = np.clip(1.0 - np.abs(d - 0.34) * float(P["thin"]), 0, 1)
        wrinkle = K.norm(K.mid(shape, float(P["wrinkle_px"]), seed + 20, octaves=2))
        return np.clip(0.55 + 0.55 * outline + 0.22 * (wrinkle - 0.5), 0, 1).astype(np.float32)

    return K.cache(("sltsh", h, w, int(seed), _k(P)), build)


def paint_slt_shed_ecdysis(paint, shape, mask, seed, pm, bb):
    """The shed itself: a papery layer carrying the ghost of the scales that made it."""
    P = _P("slt_shed_ecdysis")
    src = K.incoming(paint, shape)
    t = _shed(shape, seed, P)
    lum = src.mean(axis=2, keepdims=True)
    milky = np.clip(lum * 0.55 + 0.45, 0, 1)
    a = np.clip(t * float(P["gain"]), 0, 1)[:, :, None]
    out = src * (1.0 - 0.65 * a) + milky * (0.65 * a)
    return K.finish(out.astype(np.float32), src, mask)


def spec_slt_shed_ecdysis(shape, seed, sm, base_m, base_r):
    """GRAMMAR: translucency ramp — dead keratin scatters instead of reflecting, so
    the whole shelf's only sub-surface material lives here."""
    P = _P("slt_shed_ecdysis")
    t = _shed(shape, seed, P)
    M = np.clip(12.0 + 26.0 * t * sm, 0, 255)
    R = np.clip(190.0 - 70.0 * t, 15, 255)
    CC = np.clip(150.0 - 66.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 12 · COBRA HOOD ══
def _hood(shape, seed, P):
    """Hood scales STRETCHED wide: the same geometry, anisotropically expanded.

    The tiling is deliberately non-square — broad flattened lozenges with different
    spacing on the two axes, which is what spreading a hood physically does.
    """
    h, w = shape[:2]

    def build():
        fu, fv, iu, iv = _brick(shape, float(P["wide_px"]), float(P["tall_px"]), seed + 21)
        d = np.sqrt(fu * fu * 0.55 + fv * fv * 3.6)
        body = np.clip(1.0 - d * 1.7, 0, 1)
        rim = np.clip(1.0 - np.abs(d - 0.52) * float(P["rim"]), 0, 1)
        return np.clip(0.36 + 0.72 * body - 0.40 * rim, 0, 1).astype(np.float32)

    return K.cache(("slthd", h, w, int(seed), _k(P)), build)


def paint_slt_cobra_hood(paint, shape, mask, seed, pm, bb):
    """Hood scales pulled wide across a spread hood."""
    P = _P("slt_cobra_hood")
    src = K.incoming(paint, shape)
    t = _hood(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.46, 1.44)
    return K.finish(out, src, mask)


def spec_slt_cobra_hood(shape, seed, sm, base_m, base_r):
    """GRAMMAR: anisotropic stretched tiling — the scales are wider than they are
    tall, so the specular is too, and the spec has to be built on the same axes."""
    P = _P("slt_cobra_hood")
    t = _hood(shape, seed, P)
    M = np.clip(34.0 + 70.0 * t * sm, 0, 255)
    R = np.clip(140.0 - 72.0 * t, 15, 255)
    CC = np.clip(76.0 - 38.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════ 13 · WART SNAKE ══
def _wart(shape, seed, P):
    """Non-overlapping tubercles with BARE SKIN between them — a rasping, file-like
    surface, and the structural opposite of every overlapping-scale snake here."""
    h, w = shape[:2]

    def build():
        fu, fv, iu, iv = _brick(shape, float(P["pitch"]), float(P["pitch"]), seed + 23, stagger=0.5)
        d = np.sqrt(fu * fu + fv * fv)
        dome = np.clip(1.0 - d * float(P["round"]), 0, 1) ** 1.6
        gap = np.clip((d - 0.34) * 3.4, 0, 1)
        rough = _hash2(iu, iv, 8.2) * 0.22
        return np.clip(0.24 + 0.86 * dome + rough * dome - 0.22 * gap, 0, 1).astype(np.float32)

    return K.cache(("sltwt", h, w, int(seed), _k(P)), build)


def paint_slt_wart_tubercle(paint, shape, mask, seed, pm, bb):
    """Wart snake: granular tubercles standing proud with bare skin between them."""
    P = _P("slt_wart_tubercle")
    src = K.incoming(paint, shape)
    t = _wart(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.44, 1.38)
    return K.finish(out, src, mask)


def spec_slt_wart_tubercle(shape, seed, sm, base_m, base_r):
    """GRAMMAR: tubercle three-material — proud dome, shadowed gap and the bare skin
    beneath, which no overlapping-scale snake on this shelf ever exposes."""
    P = _P("slt_wart_tubercle")
    t = _wart(shape, seed, P)
    M = np.clip(16.0 + 44.0 * t * sm, 0, 255)
    R = np.clip(215.0 - 90.0 * t, 15, 255)
    CC = np.clip(106.0 - 48.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 14 · DIAMONDBACK ══
def _diamond(shape, seed, P):
    """Rhombic diamonds with pale borders riding on a heavily KEELED scale field.

    Two geometries stacked: the diamond at the pattern scale and the keel at the
    scale scale, and both have to stay legible at once.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        u, v = px / pitch, py / pitch
        fu = (u - np.floor(u) - 0.5)
        fv = (v - np.floor(v) - 0.5)
        l1 = np.abs(fu) + np.abs(fv)                      # rhombus in the L1 metric
        fill = np.clip((0.42 - l1) * 6.0, 0, 1)
        border = np.clip(1.0 - np.abs(l1 - 0.42) * float(P["border"]), 0, 1)
        fu2, fv2, _, _ = _brick(shape, float(P["scale_px"]), float(P["scale_px"]) * 0.7, seed + 25)
        keel = np.clip(1.0 - np.abs(fu2) * 7.0, 0, 1)
        return np.clip(0.62 - 0.44 * fill + 0.55 * border + 0.16 * keel, 0, 1).astype(np.float32)

    return K.cache(("sltdb", h, w, int(seed), _k(P)), build)


def paint_slt_diamondback(paint, shape, mask, seed, pm, bb):
    """Diamondback: pale-bordered rhombs over a keeled field."""
    P = _P("slt_diamondback")
    src = K.incoming(paint, shape)
    t = _diamond(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.40, 1.50)
    return K.finish(out, src, mask)


def spec_slt_diamondback(shape, seed, sm, base_m, base_r):
    """GRAMMAR: two-layer blotch over keel — the pattern layer and the scale layer
    deal separately, so the spec carries both at once."""
    P = _P("slt_diamondback")
    t = _diamond(shape, seed, P)
    M = np.clip(44.0 + 66.0 * t * sm, 0, 255)
    R = np.clip(178.0 - 84.0 * t, 15, 255)
    CC = np.clip(96.0 - 46.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 15 · ANACONDA OVAL ══
def _anaconda(shape, seed, P):
    """Large dark ovals with paler centres, staggered in TWO offset rows.

    The stagger is the identity: a single row of ovals is a different animal, and
    the offset is what makes an anaconda read as an anaconda.
    """
    h, w = shape[:2]

    def build():
        fu, fv, iu, iv = _brick(shape, float(P["pitch"]), float(P["pitch"]) * 0.78,
                                seed + 27, stagger=0.5)
        jx = (_hash2(iu, iv, 3.9) - 0.5) * 0.25
        d = np.sqrt((fu + jx) ** 2 * 1.0 + fv * fv * 1.7)
        oval = np.clip((float(P["size"]) - d) * float(P["soft"]), 0, 1)
        core = np.clip((float(P["size"]) * 0.45 - d) * 4.0, 0, 1)
        return np.clip(0.80 - 0.70 * oval + 0.42 * core, 0, 1).astype(np.float32)

    return K.cache(("sltan", h, w, int(seed), _k(P)), build)


def paint_slt_anaconda_oval(paint, shape, mask, seed, pm, bb):
    """Anaconda ovals: dark, staggered, each with a paler heart."""
    P = _P("slt_anaconda_oval")
    src = K.incoming(paint, shape)
    t = _anaconda(shape, seed, P)
    out = _tone(src, t * float(P["gain"]), 0.32, 1.44)
    return K.finish(out, src, mask)


def spec_slt_anaconda_oval(shape, seed, sm, base_m, base_r):
    """GRAMMAR: staggered oval domain palette — three nested materials per oval,
    laid on a two-row offset lattice."""
    P = _P("slt_anaconda_oval")
    t = _anaconda(shape, seed, P)
    M = np.clip(24.0 + 58.0 * t * sm, 0, 255)
    R = np.clip(185.0 - 78.0 * t, 15, 255)
    CC = np.clip(92.0 - 40.0 * t, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════════ 16 · ALBINO ══
def _albino(shape, seed, P):
    """Pigment gone, pattern retained as a GHOST.

    The blotch survives only as a faint warm edge, and the scales go translucent so
    light scatters a little way through them — high-key, which nothing else on this
    shelf is.
    """
    h, w = shape[:2]

    def build():
        fu, fv, iu, iv = _brick(shape, float(P["scale_px"]), float(P["scale_px"]) * 0.7, seed + 29)
        d = np.sqrt(fu * fu + fv * fv * 2.0)
        body = np.clip(1.0 - d * 1.8, 0, 1)
        ghost = K.norm(K.mid(shape, float(P["ghost_px"]), seed + 30, octaves=2))
        edge = np.clip(np.abs(ghost - 0.5) * float(P["ghost"]), 0, 1)
        return np.clip(0.62 + 0.42 * body - 0.26 * edge, 0, 1).astype(np.float32)

    return K.cache(("sltal", h, w, int(seed), _k(P)), build)


def paint_slt_albino_translucent(paint, shape, mask, seed, pm, bb):
    """Albino: the pattern survives as a ghost, the pigment does not."""
    P = _P("slt_albino_translucent")
    src = K.incoming(paint, shape)
    t = _albino(shape, seed, P)
    warm = np.clip(src * 0.45 + 0.62, 0, 1)
    a = np.clip(t * float(P["gain"]), 0, 1)[:, :, None]
    out = src * (1.0 - 0.72 * a) + warm * (0.72 * a)
    return K.finish(out.astype(np.float32), src, mask)


def spec_slt_albino_translucent(shape, seed, sm, base_m, base_r):
    """GRAMMAR: high-key subsurface ladder — with no melanin the scale scatters
    rather than absorbs, so every level sits pale and the ladder is compressed."""
    P = _P("slt_albino_translucent")
    t = _albino(shape, seed, P)
    M = np.clip(K.ladder(t, 5, 6.0, 34.0) * sm, 0, 255)
    R = np.clip(K.ladder(1.0 - t, 5, 34.0, 96.0), 15, 255)
    CC = np.clip(K.ladder(1.0 - t, 4, 20.0, 62.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)



# ══════════════════════════════════════════════════════════════ CATALOG ══
CATALOG = {
    "slt_reticulated":        {"M": 25,  "R": 105, "CC": 45,
                               "desc": "Reticulated Python — the pale net, and dark blocks inside it"},
    "slt_keeled_viper":       {"M": 40,  "R": 130, "CC": 38,
                               "desc": "Keeled Viper — a raised ridge down every single scale"},
    "slt_cycloid_gloss":      {"M": 30,  "R": 32,  "CC": 18,
                               "desc": "Sea Snake Gloss — smooth overlapping scales, wet-adapted"},
    "slt_ventral_scute":      {"M": 18,  "R": 70,  "CC": 30,
                               "desc": "Ventral Scute — the belly's wide transverse plates"},
    "slt_boa_saddle":         {"M": 22,  "R": 120, "CC": 60,
                               "desc": "Boa Saddle — dark saddles pinched at the waist"},
    "slt_sidewinder_micro":   {"M": 35,  "R": 175, "CC": 82,
                               "desc": "Sidewinder Micro — desert granules matched to sand"},
    "slt_gaboon_geometric":   {"M": 28,  "R": 145, "CC": 70,
                               "desc": "Gaboon Geometric — hourglasses with razor boundaries"},
    "slt_milk_band":          {"M": 20,  "R": 90,  "CC": 36,
                               "desc": "Milk Snake Band — tricolour bands in strict order"},
    "slt_corn_blotch":        {"M": 26,  "R": 115, "CC": 52,
                               "desc": "Corn Snake Blotch — blotches ringed in an unbroken outline"},
    "slt_sunbeam_iris":       {"M": 150, "R": 28,  "CC": 16,
                               "desc": "Sunbeam Iridescence — shimmer that lives on the scale"},
    "slt_shed_ecdysis":       {"M": 12,  "R": 155, "CC": 118,
                               "desc": "Shed Skin — the papery ghost of the scales that made it"},
    "slt_cobra_hood":         {"M": 34,  "R": 100, "CC": 42,
                               "desc": "Cobra Hood — scales pulled wide across a spread hood"},
    "slt_wart_tubercle":      {"M": 16,  "R": 195, "CC": 96,
                               "desc": "Wart Snake — granular tubercles with bare skin between"},
    "slt_diamondback":        {"M": 44,  "R": 140, "CC": 64,
                               "desc": "Diamondback — pale-bordered rhombs over a keeled field"},
    "slt_anaconda_oval":      {"M": 24,  "R": 160, "CC": 74,
                               "desc": "Anaconda Oval — dark staggered ovals with paler hearts"},
    "slt_albino_translucent": {"M": 10,  "R": 60,  "CC": 22,
                               "desc": "Albino — the pattern survives as a ghost, the pigment does not"},
}

SPACE = {
    "slt_reticulated":        {"cell_px": (16.0, 28.0), "net": (3.0, 7.0), "scale_px": (7.0, 12.0),
                               "gain": (0.70, 1.45)},
    "slt_keeled_viper":       {"scale_px": (11.0, 19.0), "keel": (3.0, 7.0), "gain": (0.70, 1.50)},
    "slt_cycloid_gloss":      {"scale_px": (12.0, 22.0), "lip": (1.6, 3.8), "gain": (0.70, 1.45)},
    "slt_ventral_scute":      {"pitch": (18.0, 30.0), "edge": (5.0, 12.0), "gain": (0.70, 1.45)},
    "slt_boa_saddle":         {"pitch": (17.0, 28.0), "waist_px": (16.0, 40.0), "scale_px": (7.0, 12.0),
                               "gain": (0.70, 1.50)},
    "slt_sidewinder_micro":   {"bead_px": (8.0, 13.0), "round": (1.7, 3.0), "gain": (0.70, 1.45)},
    "slt_gaboon_geometric":   {"pitch": (15.0, 26.0), "size": (0.30, 0.46), "hard": (5.0, 14.0),
                               "gain": (0.70, 1.50)},
    "slt_milk_band":          {"band_px": (7.0, 12.0), "gain": (0.30, 0.85)},
    "slt_corn_blotch":        {"pitch": (15.0, 26.0), "size": (0.26, 0.40), "ring": (5.0, 12.0),
                               "gain": (0.70, 1.50)},
    "slt_sunbeam_iris":       {"scale_px": (11.0, 19.0), "spread": (0.8, 2.6), "gain": (0.55, 1.05)},
    "slt_shed_ecdysis":       {"scale_px": (12.0, 20.0), "thin": (3.4, 8.0), "wrinkle_px": (14.0, 30.0),
                               "gain": (0.60, 1.20)},
    "slt_cobra_hood":         {"wide_px": (16.0, 26.0), "tall_px": (8.0, 14.0), "rim": (3.4, 8.0),
                               "gain": (0.70, 1.45)},
    "slt_wart_tubercle":      {"pitch": (10.0, 17.0), "round": (1.8, 3.2), "gain": (0.70, 1.50)},
    "slt_diamondback":        {"pitch": (18.0, 30.0), "border": (4.0, 9.0), "scale_px": (8.0, 13.0),
                               "gain": (0.70, 1.50)},
    "slt_anaconda_oval":      {"pitch": (17.0, 29.0), "size": (0.30, 0.44), "soft": (3.0, 7.0),
                               "gain": (0.70, 1.50)},
    "slt_albino_translucent": {"scale_px": (11.0, 19.0), "ghost_px": (20.0, 34.0), "ghost": (0.8, 2.2),
                               "gain": (0.55, 1.15)},
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
